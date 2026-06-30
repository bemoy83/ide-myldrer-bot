# PRD: Idé-myldrer Bot (lokal LLM)

## 1. Bakgrunn / Problem

Når man er tom for prosjektideer er det vanlig å få en lang liste med 10 generiske forslag fra en chatbot, som ikke føles tilpasset. Denne boten skal i stedet føre en kort, styrt dialog (à la "20 spørsmål") for å smalne inn på noe konkret — ett spørsmål om gangen, med svaralternativer, før den oppsummerer med 3-5 skreddersydde forslag.

Dette er v1: et software-only prototype-prosjekt som kjører helt lokalt (Ollama), uten ekstern hardware. Hvis konseptet fungerer godt kan det senere bli en fysisk enhet (se "Fremtidige iterasjoner").

## 2. Mål med v1

- Kjøre en fungerende idémyldring-samtale lokalt, fra terminal eller enkelt webgrensesnitt.
- Modellen stiller **ett spørsmål per tur**, med 2-4 konkrete svaralternativer.
- Etter 2-4 spørsmål oppsummerer modellen med 3-5 konkrete, spesifikke prosjektforslag basert på svarene som er gitt.
- Hele samtalehistorikken sendes med i hvert kall (enkel state, ingen DB nødvendig for v1).

## 3. Ikke-mål (out of scope for v1)

- Ingen fysisk enhet, knapp eller skjerm.
- Ingen tale (STT/TTS).
- Ingen persistent lagring mellom sesjoner (kan legges til senere).
- Ingen multi-bruker-støtte.
- Ingen RAG over egne dokumenter (kan bli en egen v2-retning).

## 4. Eksempel-brukerreise

1. Bruker starter appen, skriver inn et vagt utgangspunkt ("jeg vil lage noe med 3D-printer og AI").
2. Bot: stiller spørsmål 1 med 3 alternativer (f.eks. "Hva frister mest: praktisk, kunst, gadget, elektronikk?").
3. Bruker svarer (velger alternativ eller skriver fritekst).
4. Bot bygger videre, stiller spørsmål 2 basert på forrige svar.
5. Etter 2-4 runder: Bot oppsummerer med 3-5 konkrete forslag, hver med en kort begrunnelse knyttet til svarene.
6. Bruker kan be om "flere alternativer" eller "gå dypere på forslag 2" — bot fortsetter dialogen.

## 5. Funksjonelle krav

| ID  | Krav                                                                                                                                                                                  |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR1 | Systemet skal sende systemprompt + full samtalehistorikk til lokal LLM ved hvert kall                                                                                                 |
| FR2 | Modellens svar skal parses som strukturert JSON: `{"type": "question", "question": str, "options": [str]}` eller `{"type": "summary", "ideas": [{"title": str, "description": str}]}` |
| FR3 | Hvis JSON-parsing feiler, skal systemet retry-e én gang med en presiserende instruks ("Svar KUN med gyldig JSON") før det faller tilbake til rå tekst                                 |
| FR4 | Brukeren skal kunne velge et alternativ (nummer) eller skrive fritekst som svar                                                                                                       |
| FR5 | Etter et konfigurerbart antall spørsmål (default: 3) skal modellen tvinges til å oppsummere, selv om den ikke har gjort det selv                                                      |
| FR6 | Samtalen skal kunne nullstilles ("ny idé-sesjon")                                                                                                                                     |

## 6. Teknisk arkitektur

**v1 = webgrensesnitt direkte.** Backend: FastAPI (eller Flask) som eksponerer ett endpoint (`POST /chat`) som tar samtalehistorikk + brukersvar og returnerer neste strukturerte respons fra Ollama. Frontend: enkel HTML/JS-side (ingen rammeverk nødvendig for v1) som rendrer spørsmål som klikkbare knapper for alternativene, og et fritekstfelt som alltid er tilgjengelig.

```
[Browser: HTML/JS]
  - viser spørsmål + alternativ-knapper
  - POST /chat med {history, user_answer}
        |
        v
[FastAPI backend]
  - Conversation Manager (state i minnet, evt. enkel session-cookie)
  - Bygger prompt (systemprompt + historikk)
  - Kaller Ollama (localhost:11434) med format=json
  - Validerer/parser JSON-respons
        |
        v
[Ollama, lokal modell]
```

## 7. Systemprompt-spesifikasjon

Nøkkelpunkter prompten må dekke:

- Rolle: idémyldring-partner, ikke en generell assistent
- Regel: maks ett spørsmål per svar, alltid 2-4 konkrete alternativer
- Regel: bygg videre på tidligere svar — ikke still løsrevne spørsmål
- Regel: svar KUN i spesifisert JSON-format, ingen fritekst utenfor
- Few-shot-eksempel: vis 1 eksempel-runde direkte i systemprompten (mindre modeller følger format mye bedre med eksempel enn med bare beskrivelse)
- Instruks for oppsummeringsfasen: når den blir bedt om å oppsummere, skal den gi 3-5 forslag, hver med titel + 1-2 setninger begrunnelse knyttet konkret til svarene som er gitt

## 8. State-modell (forslag)

```python
{
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "<json string>"},
    ...
  ],
  "question_count": 2,
  "max_questions": 3,
  "phase": "questioning" | "summary"
}
```

## 9. Tech stack-forslag

- **Språk:** Python
- **LLM-runtime:** Ollama, lokalt
- **Modell (v1, primær):** `qwen3.5:9b` — dense 9B-modell, raskest av de tre å iterere mot, og fremhevet spesifikt som sterk på tool calling/strukturert output. Godt utgangspunkt for å få JSON-formatet stabilt.
- **Modell (alternativ, dypere resonnering):** `gpt-oss:20b` — sterkere resonnering og fullt chain-of-thought, men bruker OpenAIs "harmony"-format internt og er tregere/tyngre (trenger ~16GB minne). Verdt å teste hvis qwen3.5 gir for enkle/forutsigbare oppfølgingsspørsmål.
- **Modell (alternativ, multimodal/native system-rolle):** `gemma4` (standard = e4b-variant) — native støtte for system-rolle og function calling, kan være verdt å sammenligne hvis du senere vil legge til bilder (f.eks. skisser av prosjektidéer) i dialogen.
- **Anbefaling for v1:** start med `qwen3.5:9b`, bytt `model`-parameteren i Ollama-kallet for å A/B-teste mot de andre to — ingen kodeendring nødvendig utover det.
- **JSON-tvang:** Ollamas `format: json`-parameter for å redusere parse-feil (fungerer på tvers av alle tre modellene over)
- **Backend:** FastAPI
- **v1 UI:** enkel HTML/JS-side med klikkbare alternativ-knapper og fritekstfelt, servert direkte fra FastAPI (ingen frontend-rammeverk nødvendig)

## 10. Suksesskriterier for v1

- Kan fullføre minst 3 sammenhengende idémyldring-sesjoner uten at JSON-parsing krasjer
- Spørsmålene oppleves som å bygge logisk på hverandre (ikke tilfeldige/løsrevne)
- Sluttforslagene er konkrete og spesifikke nok til at man faktisk kunne starte å bygge dem (ikke generiske "lag en app")

## 11. Fremtidige iterasjoner (out of scope nå, men verdt å notere)

- Lagre tidligere sesjoner / favorittforslag
- Fysisk versjon: 3D-printet enhet med skjerm/knapp koblet via USB til laptop som kjører modellen
- RAG over egne notater/sangtekster/kodebase for enda mer personlig tilpassede forslag
- Tekst-til-tale for spørsmålene (rubber-duck-stil)
