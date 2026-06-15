"""Geautomatiseerde tests afgeleid van de gebruiksscenario's uit URS_v2.

Elke testklasse hoort bij één scenario uit het URS-document (sectie 3).
De docstrings verwijzen naar de gelinkte gebruikerseisen (UR-xx) zodat de
tests traceerbaar zijn naar de eisen.

De Ollama-LLM en de ChromaDB-retriever worden gemockt, zodat de tests
volledig offline en deterministisch draaien (zie ook UR-16: lokaal/offline).
"""
from types import SimpleNamespace

import pytest
from langchain_core.messages import HumanMessage

from app.agent import intent, recipe, followup, quality, response, retriever
from app.agent.graph import agent
from app.agent import memory_extractor
from app.memory import profile as profile_store


# --------------------------------------------------------------------------- #
# Hulpfuncties & fixtures
# --------------------------------------------------------------------------- #
def _state(text: str, **extra) -> dict:
    """Bouwt een minimale AgentState met één gebruikersbericht."""
    base = {
        "messages": [HumanMessage(content=text)],
        "intent": None,
        "retrieved_docs": [],
        "needs_followup": False,
        "quality_ok": False,
        "final_answer": None,
        "retry_count": 0,
        "user_profile": {},
        "available_ingredients": [],
    }
    base.update(extra)
    return base


class _FakeMessage:
    """Imiteert het resultaat van ChatOllama.invoke (.content)."""

    def __init__(self, content: str):
        self.content = content


class _FakeLLM:
    """Vervangt een ChatOllama-instantie; legt de laatste system-prompt vast."""

    def __init__(self, reply: str, sink: dict, key: str):
        self._reply, self._sink, self._key = reply, sink, key

    def invoke(self, messages):
        self._sink[self._key] = messages[0].content
        return _FakeMessage(self._reply)


@pytest.fixture
def fake_llm(monkeypatch):
    """Vervangt alle LLM-calls door opvangers die de system-prompt vastleggen.

    ChatOllama is een Pydantic-model (geen losse attributen toegestaan), daarom
    vervangen we het hele ``_llm``-object per node. Het teruggegeven dict bevat
    de laatst geziene system-prompt, zodat tests kunnen controleren welke
    instructies aan het model zijn meegegeven.
    """
    captured = {"recipe_system": None, "followup_system": None}

    recipe_reply = (
        "Hier is je energie-smoothie 🍌🥬\n"
        "Ingrediënten: banaan, spinazie, havermout.\n"
        "Bereiding: alles mixen.\n"
        "📊 Geschatte calorieën: ~250 kcal per portie."
    )
    followup_reply = "Oh leuk, vertel me meer! Wat wil je graag bereiken?"

    monkeypatch.setattr(recipe, "_llm", _FakeLLM(recipe_reply, captured, "recipe_system"))
    monkeypatch.setattr(followup, "_llm", _FakeLLM(followup_reply, captured, "followup_system"))
    return captured


@pytest.fixture
def fake_retriever(monkeypatch):
    """Vervangt embeddings + ChromaDB door vaste voedingsdocumenten."""
    docs = [
        "IJzer draagt bij aan een normaal energieniveau. Bron: RIVM Voedingsnormen.",
        "Vitamine B12 helpt tegen vermoeidheid. Bron: Voedingscentrum.",
    ]
    monkeypatch.setattr(retriever, "_embeddings", SimpleNamespace(embed_query=lambda q: [0.0, 0.1, 0.2]))
    monkeypatch.setattr(retriever.vector_store, "query", lambda embedding, top_k: docs)
    return docs


@pytest.fixture
def no_normalize(monkeypatch):
    """Schakelt de LLM-spellingcorrectie in de memory-extractor uit."""
    monkeypatch.setattr(memory_extractor, "_normalize_labels", lambda items: items)


# --------------------------------------------------------------------------- #
# Scenario 1 — Doelgericht recept (kern)
# Gelinkte eisen: UR-06, UR-08, UR-11, UR-13, UR-18
# --------------------------------------------------------------------------- #
class TestScenario1DoelgerichtRecept:
    QUERY = "Ik wil een smoothie die me meer energie geeft"

    def test_intent_herkend_als_recept(self):
        """UR-03/UR-06: doelgerichte receptvraag wordt als 'recipe' herkend."""
        result = intent.run(_state(self.QUERY))
        assert result["intent"] == "recipe"
        assert result["needs_followup"] is False  # 'energie' is specifiek genoeg

    def test_recipe_prompt_vraagt_kcal(self, fake_llm):
        """UR-08: het recept bevat een geschatte caloriewaarde."""
        state = _state(self.QUERY, retrieved_docs=["IJzer geeft energie."])
        out = recipe.run(state)
        assert "kcal" in out["final_answer"].lower()
        assert "kcal" in fake_llm["recipe_system"].lower()

    def test_recipe_prompt_vraagt_voedingsstoffen_met_bron(self, fake_llm):
        """UR-11/UR-12: voedingsstoffen + herleidbare bron (RIVM) worden gevraagd."""
        recipe.run(_state(self.QUERY, retrieved_docs=["IJzer geeft energie."]))
        sys = fake_llm["recipe_system"]
        assert "Voedingsstoffen" in sys
        assert "RIVM" in sys

    def test_eind_tot_eind_levert_recept_met_disclaimer(self, fake_llm, fake_retriever):
        """UR-13/UR-18: volledige flow levert een onderbouwd recept met disclaimer."""
        final = agent.invoke(_state(self.QUERY))
        assert "kcal" in final["final_answer"].lower()
        assert "Disclaimer" in final["final_answer"]


# --------------------------------------------------------------------------- #
# Scenario 2 — Koelkast-modus
# Gelinkte eisen: UR-07, UR-08, UR-10, UR-18
# --------------------------------------------------------------------------- #
class TestScenario2KoelkastModus:
    QUERY = "Ik heb alleen banaan, havermout en spinazie"

    def test_beschikbare_ingredienten_geextraheerd(self, no_normalize):
        """UR-07: 'ik heb alleen ...' wordt herkend als beschikbare ingrediënten."""
        updates = memory_extractor._extract(self.QUERY)
        assert set(updates.get("available_ingredients", [])) == {
            "banaan",
            "havermout",
            "spinazie",
        }

    def test_recipe_prompt_beperkt_tot_beschikbare_ingredienten(self, fake_llm):
        """UR-07: prompt instrueert om alleen beschikbare ingrediënten te gebruiken."""
        state = _state(
            self.QUERY,
            available_ingredients=["banaan", "havermout", "spinazie"],
            retrieved_docs=["doc"],
        )
        sys = recipe.build_system_message(state).content
        assert "banaan" in sys and "havermout" in sys and "spinazie" in sys
        assert "alleen de volgende ingrediënten" in sys

    def test_recipe_prompt_vraagt_alternatief_bij_tekort(self, fake_llm):
        """UR-10: prompt vraagt om alternatief + benodigde aanvulling bij tekort."""
        state = _state(self.QUERY, available_ingredients=["banaan"], retrieved_docs=["doc"])
        sys = recipe.build_system_message(state).content
        assert "alternatief" in sys.lower()
        assert "nog nodig hebt" in sys.lower()


# --------------------------------------------------------------------------- #
# Scenario 3 — Dieetvoorkeur (vegan)
# Gelinkte eisen: UR-09, UR-06, UR-08, UR-18
# --------------------------------------------------------------------------- #
class TestScenario3DieetvoorkeurVegan:
    QUERY = "Geef me een proteïne-smoothie, maar ik eet vegan"

    def test_dieetvoorkeur_geextraheerd(self, no_normalize):
        """UR-09: de dieetvoorkeur 'vegan' wordt geregistreerd als 'veganistisch'."""
        updates = memory_extractor._extract(self.QUERY)
        assert "veganistisch" in updates.get("preferences", [])

    def test_recipe_prompt_dwingt_vegan_af(self, fake_llm):
        """UR-09: vegan-profiel leidt tot harde 'geen dierlijke producten'-regel."""
        profile = {"preferences": ["veganistisch"]}
        state = _state(self.QUERY, user_profile=profile, retrieved_docs=["doc"])
        sys = recipe.build_system_message(state).content
        assert "geen dierlijke producten" in sys
        assert "NOOIT" in sys  # strikte formulering

    def test_notenvrije_voorkeur_wordt_strikt_vermeld(self, fake_llm):
        """UR-09: ook notenvrij wordt als harde regel in de prompt gezet."""
        state = _state(
            "Geef me een smoothie",
            user_profile={"preferences": ["notenvrij"]},
            retrieved_docs=["doc"],
        )
        sys = recipe.build_system_message(state).content
        assert "geen noten" in sys.lower()


# --------------------------------------------------------------------------- #
# Scenario 4 — Vage klacht, gericht advies (agentic doorvragen)
# Gelinkte eisen: UR-03, UR-04, UR-06, UR-08, UR-11, UR-13
# --------------------------------------------------------------------------- #
class TestScenario4VageKlacht:
    # Een gevoelsklacht; de implementatie behandelt dit als een actiegerichte,
    # empathische receptvraag (zie design-notitie in het testdocument).
    GEVOEL = "Ik voel me moe"
    # Een écht onbepaalde vraag zonder doel/ingrediënt/context.
    VAAG = "Heb je een tip?"

    def test_gevoelsklacht_herkend_als_recept(self):
        """UR-03: een vage gevoelsklacht wordt begrepen en als receptvraag herkend."""
        result = intent.run(_state(self.GEVOEL))
        assert result["intent"] == "recipe"
        # Design-keuze: meteen empathisch recept i.p.v. doorvragen.
        assert result["needs_followup"] is False

    def test_te_vage_vraag_triggert_followup(self):
        """UR-04: een vraag zonder doel/context leidt tot een gerichte vervolgvraag."""
        result = intent.run(_state(self.VAAG))
        assert result["needs_followup"] is True

    def test_followup_node_stelt_een_vraag(self, fake_llm):
        """UR-04: de followup-node retourneert een gerichte vervolgvraag."""
        out = followup.run(_state(self.VAAG))
        assert out["final_answer"]
        assert "?" in out["final_answer"]

    def test_graph_routeert_vage_vraag_naar_followup(self, fake_llm, fake_retriever):
        """UR-03/UR-04: de graph eindigt bij followup en genereert (nog) geen recept."""
        final = agent.invoke(_state(self.VAAG))
        # Followup-antwoord, dus geen kcal-recept.
        assert "?" in final["final_answer"]
        assert "kcal" not in final["final_answer"].lower()

    def test_context_maakt_vraag_actiegericht(self):
        """UR-03: een recept-vraag zonder specifics is vaag, maar wordt actiegericht
        zodra het profiel een doel kent."""
        query = "Maak eens een smoothie"  # duidelijke recept-intent, geen specifics
        zonder_profiel = intent.run(_state(query))
        met_profiel = intent.run(_state(query, user_profile={"goals": ["meer energie"]}))
        assert zonder_profiel["needs_followup"] is True
        assert met_profiel["needs_followup"] is False


# --------------------------------------------------------------------------- #
# Scenario 5 — Proactieve suggestie
# Gelinkte eisen: UR-01, UR-02, UR-05
# --------------------------------------------------------------------------- #
class TestScenario5ProactieveSuggestie:
    def test_reactie_op_suggestie_levert_recept(self, fake_llm, fake_retriever):
        """UR-02/UR-05: ingaan op een proactieve suggestie genereert een recept."""
        final = agent.invoke(_state("Ja, maak die energieboost-smoothie maar"))
        assert "kcal" in final["final_answer"].lower()
        assert "Disclaimer" in final["final_answer"]


# --------------------------------------------------------------------------- #
# Aanvullende eisen die over alle scenario's heen gelden
# --------------------------------------------------------------------------- #
class TestKwaliteitsEnVeiligheidsEisen:
    def test_disclaimer_altijd_aanwezig(self):
        """UR-13: elk eindantwoord bevat de niet-medisch-advies-disclaimer."""
        out = response.run(_state("x", final_answer="Een prima recept met genoeg tekst erbij."))
        assert "geen professioneel medisch" in out["final_answer"]

    def test_kwaliteitscheck_keurt_te_kort_antwoord_af(self):
        """Kwaliteitslus: een te kort antwoord (<80 tekens) is niet 'ok'."""
        out = quality.run(_state("x", final_answer="Te kort."))
        assert out["quality_ok"] is False

    def test_kwaliteitscheck_keurt_volledig_antwoord_goed(self):
        """Kwaliteitslus: een voldoende lang antwoord wordt goedgekeurd."""
        out = quality.run(_state("x", final_answer="x" * 100))
        assert out["quality_ok"] is True


# --------------------------------------------------------------------------- #
# Privacy & persistente memory (UR-14, UR-15)
# --------------------------------------------------------------------------- #
class TestPrivacyEnMemory:
    def test_profiel_lokaal_opgeslagen_en_geladen(self, tmp_path, monkeypatch):
        """UR-14/UR-15: profiel wordt lokaal als JSON bewaard, zonder account."""
        monkeypatch.setattr(profile_store, "_PROFILES_DIR", tmp_path)
        profile_store.save("sessie-test", {"name": "Ruyi", "goals": ["meer energie"]})
        loaded = profile_store.load("sessie-test")
        assert loaded["name"] == "Ruyi"
        assert (tmp_path / "sessie-test.json").exists()

    def test_doel_geextraheerd_uit_natuurlijke_taal(self, no_normalize):
        """UR-03: een doel in alledaagse taal wordt herkend en opgeslagen."""
        updates = memory_extractor._extract("Ik wil meer energie en gezonder eten")
        assert "meer energie" in updates.get("goals", [])
        assert "gezonder eten" in updates.get("goals", [])
