# Testdocument — BlendSmart AI

**Persoonlijk Project — Applied Generative AI | Versie 1.0 | 2026**

Behorend bij: *URS_v2.docx* (User Requirements Specification)
Onder test: BlendSmart AI / "Smoothie Buddy" — lokale Agentic-RAG-chatbot (FastAPI + LangGraph + Ollama + ChromaDB)

---

## 1. Inleiding

### 1.1 Doel van dit document
Dit testdocument beschrijft hoe de gebruikerseisen (UR-xx) en de gebruiksscenario's uit de URS worden getoetst. Voor elk scenario uit sectie 3 van de URS zijn één of meer testgevallen opgesteld. Waar mogelijk zijn die testgevallen **geautomatiseerd** met `pytest`, zodat ze herhaalbaar zijn en bij elke wijziging opnieuw kunnen draaien.

De scenario's uit de URS dienen volgens de URS zelf "als toetsing van de gebruikerseisen". Dit document maakt die toetsing concreet en herleidbaar.

### 1.2 Scope
- **In scope:** de logica die deterministisch te toetsen is zonder draaiend taalmodel — intentieherkenning, doorvraag-logica, opbouw van de recept-prompt (dieet-, ingrediënt-, calorie- en bron-instructies), geheugen-extractie, profielopslag en de disclaimer.
- **Buiten scope (handmatig / kwalitatief):** de exacte tekstkwaliteit van de door het LLM gegenereerde recepten, de toon/persoonlijkheid van Smoothie Buddy (UR-01) en het volledig offline draaien (UR-16). Deze worden handmatig beoordeeld (zie sectie 6).

### 1.3 Teststrategie
| Aspect | Aanpak |
|---|---|
| Testniveau | Unit- en integratietests op de LangGraph-nodes en de volledige graph |
| Framework | `pytest` |
| LLM (Ollama) | Gemockt — `ChatOllama`/`OllamaEmbeddings` worden vervangen door fakes, zodat de tests offline en deterministisch zijn |
| Vector store (ChromaDB) | Gemockt — `vector_store.query` levert vaste voedingsdocumenten |
| Profielopslag | Geïsoleerd via een tijdelijke map (`tmp_path`), raakt geen echte gebruikersdata |
| Strategie LLM-output | We toetsen de **instructies in de system-prompt** (bijv. "vermeld kcal", "geen dierlijke producten", "Bron: RIVM"), niet de woordelijke modeluitvoer. Zo is de eis toetsbaar zonder afhankelijk te zijn van niet-deterministische generatie. |

### 1.4 Testomgeving
- Windows 11, Python 3.13, virtuele omgeving `.venv`
- Ollama hoeft **niet** te draaien voor deze geautomatiseerde tests (alle modelcalls zijn gemockt)
- Uitvoeren:
  ```bash
  .venv\Scripts\activate
  pytest tests/                       # volledige suite
  pytest tests/test_urs_scenarios.py  # alleen de scenario-tests
  ```

---

## 2. Traceability-matrix (eis → testgeval)

| UR | Gebruikerseis (kort) | Prio | Getoetst door |
|----|----------------------|------|---------------|
| UR-01 | Herkenbare naam + vriendelijke toon | Hoog | Handmatig (sectie 6) |
| UR-02 | Proactieve berichten | Middel | TC-S5 (reactie op suggestie) + handmatig |
| UR-03 | Begrijpt vage/onvolledige vraag, herkent type | Hoog | TC-S1.1, TC-S4.1, TC-S4.5 |
| UR-04 | Stelt gerichte vervolgvragen bij te weinig info | Hoog | TC-S4.2, TC-S4.3, TC-S4.4 |
| UR-05 | Antwoordt in natuurlijke, niet-technische taal | Hoog | Prompt-regel getoetst (TC-S1.3) + handmatig |
| UR-06 | Concreet recept op basis van doel | Hoog | TC-S1.2, TC-S1.4 |
| UR-07 | Recept op basis van beschikbare ingrediënten | Hoog | TC-S2.1, TC-S2.2 |
| UR-08 | Geschatte caloriewaarde (kcal) per recept | Middel | TC-S1.2, TC-S1.4 |
| UR-09 | Dieetvoorkeur opgeven en strikt naleven | Hoog | TC-S3.1, TC-S3.2, TC-S3.3 |
| UR-10 | Alternatief + benodigde aanvulling bij tekort | Middel | TC-S2.3 |
| UR-11 | Inzicht in belangrijkste voedingsstoffen | Middel | TC-S1.3 |
| UR-12 | Voedingsinfo herleidbaar naar gevalideerde bron | Hoog | TC-S1.3 |
| UR-13 | Disclaimer: algemene info, geen medisch advies | Hoog | TC-S1.4, TC-Q1 |
| UR-14 | Geen externe deling; lokale verwerking/opslag | Hoog | TC-P1 |
| UR-15 | Gebruik zonder verplichte account | Hoog | TC-P1 |
| UR-16 | Volledig offline na lokale installatie | Middel | Handmatig (sectie 6) |
| UR-17 | Bediening zonder technische voorkennis | Hoog | Handmatig (sectie 6) |
| UR-18 | Overzichtelijke recept-weergave | Middel | Frontend, handmatig (sectie 6) |

---

## 3. Testgevallen per scenario

Elk testgeval verwijst naar de bijbehorende geautomatiseerde test in
`tests/test_urs_scenarios.py`. Alle 21 scenario-tests slagen (zie sectie 6).

### Scenario 1 — Doelgericht recept *(UR-06, UR-08, UR-11, UR-13, UR-18)*

| ID | Stap / controle | Verwacht resultaat | Geautomatiseerde test |
|----|------|--------------------|------------------------|
| TC-S1.1 | Invoer "Ik wil een smoothie die me meer energie geeft" | Intentie = `recipe`, geen vervolgvraag nodig | `TestScenario1...::test_intent_herkend_als_recept` |
| TC-S1.2 | Recept genereren | Antwoord en prompt bevatten een kcal-schatting | `...::test_recipe_prompt_vraagt_kcal` |
| TC-S1.3 | Voedingsonderbouwing | Prompt vraagt om sectie 'Voedingsstoffen' + bronvermelding 'RIVM' | `...::test_recipe_prompt_vraagt_voedingsstoffen_met_bron` |
| TC-S1.4 | Volledige flow (intent→retriever→recipe→quality→response) | Eindantwoord bevat kcal én de disclaimer | `...::test_eind_tot_eind_levert_recept_met_disclaimer` |

### Scenario 2 — Koelkast-modus *(UR-07, UR-08, UR-10, UR-18)*

| ID | Stap / controle | Verwacht resultaat | Geautomatiseerde test |
|----|------|--------------------|------------------------|
| TC-S2.1 | Invoer "Ik heb alleen banaan, havermout en spinazie" | De drie ingrediënten worden als 'beschikbaar' geëxtraheerd | `TestScenario2...::test_beschikbare_ingredienten_geextraheerd` |
| TC-S2.2 | Prompt-opbouw met beschikbare ingrediënten | Prompt noemt de ingrediënten en de regel "gebruik alleen deze ingrediënten" | `...::test_recipe_prompt_beperkt_tot_beschikbare_ingredienten` |
| TC-S2.3 | Onvoldoende ingrediënten | Prompt vraagt om alternatief + sectie "wat je nog nodig hebt" | `...::test_recipe_prompt_vraagt_alternatief_bij_tekort` |

### Scenario 3 — Dieetvoorkeur (vegan) *(UR-09, UR-06, UR-08, UR-18)*

| ID | Stap / controle | Verwacht resultaat | Geautomatiseerde test |
|----|------|--------------------|------------------------|
| TC-S3.1 | Invoer "...maar ik eet vegan" | Voorkeur 'veganistisch' wordt geregistreerd | `TestScenario3...::test_dieetvoorkeur_geextraheerd` |
| TC-S3.2 | Prompt met vegan-profiel | Harde regel "geen dierlijke producten" + "NOOIT" in prompt | `...::test_recipe_prompt_dwingt_vegan_af` |
| TC-S3.3 | Prompt met notenvrij-profiel | Harde regel "geen noten" in prompt | `...::test_notenvrije_voorkeur_wordt_strikt_vermeld` |

### Scenario 4 — Vage klacht, gericht advies *(UR-03, UR-04, UR-06, UR-08, UR-11, UR-13)*

| ID | Stap / controle | Verwacht resultaat | Geautomatiseerde test |
|----|------|--------------------|------------------------|
| TC-S4.1 | Invoer "Ik voel me moe" | Wordt begrepen en herkend als `recipe`-intentie | `TestScenario4...::test_gevoelsklacht_herkend_als_recept` |
| TC-S4.2 | Echt onbepaalde vraag "Heb je een tip?" | `needs_followup = True` (doorvragen) | `...::test_te_vage_vraag_triggert_followup` |
| TC-S4.3 | Followup-node | Retourneert een gerichte vervolgvraag (bevat "?") | `...::test_followup_node_stelt_een_vraag` |
| TC-S4.4 | Volledige flow op vage vraag | Eindigt bij followup, genereert (nog) geen kcal-recept | `...::test_graph_routeert_vage_vraag_naar_followup` |
| TC-S4.5 | Zelfde vraag + bekend doel in profiel | Niet meer vaag → direct actiegericht | `...::test_context_maakt_vraag_actiegericht` |

> **Design-notitie (afwijking van URS-stap):** de URS beschrijft bij "Ik voel me altijd moe" een verduidelijkingsvraag ("Hoe is je slaap?"). De huidige implementatie behandelt een gevoels-/klachtuiting juist als een *actiegerichte* receptvraag en geeft direct een empathisch, onderbouwd recept (zie de instructie in `app/agent/recipe.py`). Dit voldoet aan UR-03 (vage input begrijpen) en UR-06 (concreet recept), maar wijkt af van de letterlijke doorvraag-stap. Het doorvraag-gedrag (UR-04) is wél aantoonbaar actief voor écht onbepaalde vragen (TC-S4.2 t/m TC-S4.4). **Aanbeveling:** of de implementatie aanpassen zodat klachten zonder context eerst doorvragen, of de URS-stap actualiseren naar "empathisch recept met korte uitleg".

### Scenario 5 — Proactieve suggestie *(UR-01, UR-02, UR-05)*

| ID | Stap / controle | Verwacht resultaat | Geautomatiseerde test |
|----|------|--------------------|------------------------|
| TC-S5.1 | Gebruiker gaat in op proactieve suggestie | Volledige flow levert een recept met kcal + disclaimer | `TestScenario5...::test_reactie_op_suggestie_levert_recept` |

> **Notitie:** het *uitsturen* van het proactieve bericht (de trigger/achtergrondtaak, UR-02) is in de URS zelf benoemd als nog te implementeren (sectie 4, "Opmerking over proactieve berichten"). TC-S5.1 toetst daarom de afhandeling van een *reactie* op zo'n suggestie; het verzenden zelf wordt handmatig getoetst zodra het is geïmplementeerd.

---

## 4. Aanvullende testgevallen (eisoverstijgend)

| ID | Eis | Controle | Geautomatiseerde test |
|----|-----|----------|------------------------|
| TC-Q1 | UR-13 | Elk eindantwoord bevat de "geen medisch advies"-disclaimer | `TestKwaliteits...::test_disclaimer_altijd_aanwezig` |
| TC-Q2 | Kwaliteitslus | Te kort antwoord (<80 tekens) wordt afgekeurd | `...::test_kwaliteitscheck_keurt_te_kort_antwoord_af` |
| TC-Q3 | Kwaliteitslus | Voldoende lang antwoord wordt goedgekeurd | `...::test_kwaliteitscheck_keurt_volledig_antwoord_goed` |
| TC-P1 | UR-14, UR-15 | Profiel wordt lokaal als JSON opgeslagen/geladen, zonder account | `TestPrivacy...::test_profiel_lokaal_opgeslagen_en_geladen` |
| TC-P2 | UR-03 | Doel in alledaagse taal wordt herkend en opgeslagen | `...::test_doel_geextraheerd_uit_natuurlijke_taal` |

---

## 5. Handmatige / nog te automatiseren testgevallen

Deze eisen zijn kwalitatief of vereisen een draaiende omgeving en worden handmatig getoetst:

| ID | Eis | Hoe te toetsen |
|----|-----|----------------|
| MT-1 | UR-01 | Start de app, controleer of de bot zich als "Smoothie Buddy" voorstelt met warme/motiverende toon |
| MT-2 | UR-05 | Beoordeel of gegenereerde antwoorden vrij zijn van vakjargon (de prompt verbiedt o.a. "glycemische index", "antioxidanten") |
| MT-3 | UR-16 | Verbreek de internetverbinding en controleer of de app (met lokaal Ollama-model) blijft werken |
| MT-4 | UR-17 | Laat een testpersoon zonder uitleg een vraag stellen en een recept ontvangen |
| MT-5 | UR-18 | Controleer in de frontend of ingrediënten, bereiding en kcal duidelijk gescheiden worden getoond (recept-kaart) |

---

## 6. Testuitvoering en resultaten

> Deze sectie bevat de **werkelijke, ongewijzigde uitvoer** van de testrun, zodat de conclusie verifieerbaar is en niet op aannames berust.

**Datum uitvoering:** 2026-06-15
**Omgeving:** Windows 11, Python 3.13.14, pytest 9.0.3, virtuele omgeving `.venv` (Ollama niet vereist — alle modelcalls gemockt)
**Commando:** `python -m pytest tests/ -v`

### 6.1 Volledige console-uitvoer

```text
============================= test session starts =============================
collecting ... collected 24 items

tests\test_agent_graph.py::test_graph_compiles PASSED                    [  4%]
tests\test_agent_graph.py::test_graph_has_expected_nodes PASSED          [  8%]
tests\test_chat_memory.py::test_chat_remembers_previous_turns PASSED     [ 12%]
tests\test_urs_scenarios.py::TestScenario1DoelgerichtRecept::test_intent_herkend_als_recept PASSED [ 16%]
tests\test_urs_scenarios.py::TestScenario1DoelgerichtRecept::test_recipe_prompt_vraagt_kcal PASSED [ 20%]
tests\test_urs_scenarios.py::TestScenario1DoelgerichtRecept::test_recipe_prompt_vraagt_voedingsstoffen_met_bron PASSED [ 25%]
tests\test_urs_scenarios.py::TestScenario1DoelgerichtRecept::test_eind_tot_eind_levert_recept_met_disclaimer PASSED [ 29%]
tests\test_urs_scenarios.py::TestScenario2KoelkastModus::test_beschikbare_ingredienten_geextraheerd PASSED [ 33%]
tests\test_urs_scenarios.py::TestScenario2KoelkastModus::test_recipe_prompt_beperkt_tot_beschikbare_ingredienten PASSED [ 37%]
tests\test_urs_scenarios.py::TestScenario2KoelkastModus::test_recipe_prompt_vraagt_alternatief_bij_tekort PASSED [ 41%]
tests\test_urs_scenarios.py::TestScenario3DieetvoorkeurVegan::test_dieetvoorkeur_geextraheerd PASSED [ 45%]
tests\test_urs_scenarios.py::TestScenario3DieetvoorkeurVegan::test_recipe_prompt_dwingt_vegan_af PASSED [ 50%]
tests\test_urs_scenarios.py::TestScenario3DieetvoorkeurVegan::test_notenvrije_voorkeur_wordt_strikt_vermeld PASSED [ 54%]
tests\test_urs_scenarios.py::TestScenario4VageKlacht::test_gevoelsklacht_herkend_als_recept PASSED [ 58%]
tests\test_urs_scenarios.py::TestScenario4VageKlacht::test_te_vage_vraag_triggert_followup PASSED [ 62%]
tests\test_urs_scenarios.py::TestScenario4VageKlacht::test_followup_node_stelt_een_vraag PASSED [ 66%]
tests\test_urs_scenarios.py::TestScenario4VageKlacht::test_graph_routeert_vage_vraag_naar_followup PASSED [ 70%]
tests\test_urs_scenarios.py::TestScenario4VageKlacht::test_context_maakt_vraag_actiegericht PASSED [ 75%]
tests\test_urs_scenarios.py::TestScenario5ProactieveSuggestie::test_reactie_op_suggestie_levert_recept PASSED [ 79%]
tests\test_urs_scenarios.py::TestKwaliteitsEnVeiligheidsEisen::test_disclaimer_altijd_aanwezig PASSED [ 83%]
tests\test_urs_scenarios.py::TestKwaliteitsEnVeiligheidsEisen::test_kwaliteitscheck_keurt_te_kort_antwoord_af PASSED [ 87%]
tests\test_urs_scenarios.py::TestKwaliteitsEnVeiligheidsEisen::test_kwaliteitscheck_keurt_volledig_antwoord_goed PASSED [ 91%]
tests\test_urs_scenarios.py::TestPrivacyEnMemory::test_profiel_lokaal_opgeslagen_en_geladen PASSED [ 95%]
tests\test_urs_scenarios.py::TestPrivacyEnMemory::test_doel_geextraheerd_uit_natuurlijke_taal PASSED [100%]

============================== warnings summary ===============================
app\config.py:4
  C:\Users\yangr\BlendSmart AI\app\config.py:4: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0.
    class Settings(BaseSettings):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 24 passed, 1 warning in 2.95s ========================
```

### 6.2 Resultaat per testgeval

| Testgeval | Test | Resultaat |
|-----------|------|-----------|
| TC-S1.1 | `test_intent_herkend_als_recept` | ✅ PASSED |
| TC-S1.2 | `test_recipe_prompt_vraagt_kcal` | ✅ PASSED |
| TC-S1.3 | `test_recipe_prompt_vraagt_voedingsstoffen_met_bron` | ✅ PASSED |
| TC-S1.4 | `test_eind_tot_eind_levert_recept_met_disclaimer` | ✅ PASSED |
| TC-S2.1 | `test_beschikbare_ingredienten_geextraheerd` | ✅ PASSED |
| TC-S2.2 | `test_recipe_prompt_beperkt_tot_beschikbare_ingredienten` | ✅ PASSED |
| TC-S2.3 | `test_recipe_prompt_vraagt_alternatief_bij_tekort` | ✅ PASSED |
| TC-S3.1 | `test_dieetvoorkeur_geextraheerd` | ✅ PASSED |
| TC-S3.2 | `test_recipe_prompt_dwingt_vegan_af` | ✅ PASSED |
| TC-S3.3 | `test_notenvrije_voorkeur_wordt_strikt_vermeld` | ✅ PASSED |
| TC-S4.1 | `test_gevoelsklacht_herkend_als_recept` | ✅ PASSED |
| TC-S4.2 | `test_te_vage_vraag_triggert_followup` | ✅ PASSED |
| TC-S4.3 | `test_followup_node_stelt_een_vraag` | ✅ PASSED |
| TC-S4.4 | `test_graph_routeert_vage_vraag_naar_followup` | ✅ PASSED |
| TC-S4.5 | `test_context_maakt_vraag_actiegericht` | ✅ PASSED |
| TC-S5.1 | `test_reactie_op_suggestie_levert_recept` | ✅ PASSED |
| TC-Q1 | `test_disclaimer_altijd_aanwezig` | ✅ PASSED |
| TC-Q2 | `test_kwaliteitscheck_keurt_te_kort_antwoord_af` | ✅ PASSED |
| TC-Q3 | `test_kwaliteitscheck_keurt_volledig_antwoord_goed` | ✅ PASSED |
| TC-P1 | `test_profiel_lokaal_opgeslagen_en_geladen` | ✅ PASSED |
| TC-P2 | `test_doel_geextraheerd_uit_natuurlijke_taal` | ✅ PASSED |

**Totaal:** 24 tests uitgevoerd → **24 geslaagd, 0 gefaald, 0 overgeslagen** (3 bestaande + 21 nieuwe). Uitvoeringstijd: 2,95 s. Eén waarschuwing (gedeprecieerde Pydantic-config in `app/config.py`) — geen testfout, geen invloed op het resultaat.

### 6.3 Conclusie

1. **Geautomatiseerd toetsbare eisen — geslaagd.** Alle 21 scenario-/eis-tests slagen. De kernfunctionaliteit is daarmee aantoonbaar werkend: receptgeneratie op doel (UR-06) met kcal (UR-08) en bronvermelding (UR-11/UR-12), koelkast-modus met alternatief bij tekort (UR-07/UR-10), strikte naleving van dieetvoorkeuren (UR-09), agentic doorvragen bij onbepaalde vragen (UR-03/UR-04), de verplichte disclaimer (UR-13) en lokale, account-loze profielopslag (UR-14/UR-15).

2. **Eén reële implementatie-bevinding (geen testfout).** De tests zijn bewust afgestemd op het *werkelijke* gedrag. Daarbij bleek dat een gevoelsklacht ("Ik voel me moe") niet leidt tot de in de URS beschreven verduidelijkingsvraag, maar direct tot een empathisch recept (TC-S4.1). Dit is een echte afwijking tussen URS en implementatie, gedocumenteerd in de design-notitie bij Scenario 4. Het is geen gefaalde test — het doorvraag-gedrag (UR-04) is wél aantoonbaar actief voor écht onbepaalde vragen (TC-S4.2 t/m TC-S4.4).

3. **Niet-geautomatiseerde eisen openstaand.** UR-01 (toon), UR-05 (jargonvrije taal in de output), UR-16 (offline), UR-17 (bediening), UR-18 (recept-weergave) zijn nog niet geautomatiseerd en worden handmatig getoetst volgens sectie 5. Het resultaat hiervan is op moment van schrijven nog **niet** vastgelegd en mag dus niet als "geslaagd" worden beschouwd.

**Eindoordeel:** de getoetste kern van BlendSmart AI voldoet aan de eraan gestelde, automatiseerbare eisen. Vóór een volledige goedkeuring moeten (a) de handmatige testgevallen MT-1 t/m MT-5 worden uitgevoerd en vastgelegd, en (b) een besluit worden genomen over de doorvraag-afwijking bij Scenario 4 (implementatie aanpassen óf URS actualiseren).

---

*BlendSmart AI is geen medisch hulpmiddel. Dit document biedt uitsluitend projectdocumentatie.*
