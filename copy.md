# Functioneel Ontwerp – ISU Data Pipeline
 
## 1. Inleiding
Dit document beschrijft het functioneel ontwerp van een geautomatiseerde data pipeline voor het verzamelen, verrijken en structureren van data over schaatswedstrijden. De pipeline is ontworpen om data uit de officiële API van de International Skating Union (ISU) te extraheren. Vervolgens wordt deze data verrijkt met **unieke ID's voor schaatsers**, hun **beste tijden van het voorgaande seizoen**, geografische locaties (steden) om daarmee via de Open-Meteo API historische weergegevens op te halen, en als laatste stap worden de afgeleide metrieken EstimatedTFM (Time From Mopping) en EstimatedTFMBuffer berekend en toegevoegd. Het eindresultaat van de pipeline bestaat uit twee analyseklare CSV-bestanden en een gestructureerde SQLite database.

## 2. Doelstelling en Probleemomschrijving
De ruwe data uit de ISU API, hoewel compleet, is niet direct geschikt voor diepgaande analyse. Dit project lost de volgende knelpunten op:
•	**Datacollectie**: Het handmatig verzamelen van wedstrijddata is een tijdrovend en foutgevoelig proces. De pipeline automatiseert dit volledig.
•	**Dataverrijking**: Essentiële context ontbreekt, zoals:
    - Een **unieke, stabiele identifier** per schaatser om prestaties over tijd te volgen.
    - Een **prestatie-baseline** (zoals de seizoensbeste tijd van vorig jaar).
    - De **geografische locaties** van de ijsbanen en de weersomstandigheden (buitentemperatuur, luchtdruk).
•	**Afgeleide metrieken**: Voor de analyse is de metriek EstimatedTFM cruciaal. Deze waarde, die de tijd sinds de laatste ijspreparatie per paar berekent, is afhankelijk van de afstand en moet voor elke rit worden berekend.

Het hoofddoel is het produceren van een betrouwbare, gestructureerde en significant verrijkte dataset die als solide basis kan dienen voor toekomstige data-analyse en het trainen van voorspellende modellen.

## 3. Systeemoverzicht en ETL-Proces
De data pipeline volgt een klassiek ETL-proces (Extract, Transform, Load). Het proces is opgedeeld in logische, onafhankelijke fases die sequentieel worden uitgevoerd door een masterscript: `run_workflow.py`.

### 3.1. Fase 1: Extract (Data-extractie)
De extractiefase vormt het fundament van de pipeline en wordt uitgevoerd door **`isu_scraper.py`**. De kwaliteit van de hier verzamelde data is bepalend voor het eindresultaat.
•	**Architectuur**: Om het extractieproces te versnellen, is de scraper gebouwd met een multi-threaded architectuur. API-calls worden parallel uitgevoerd met een `ThreadPoolExecutor`. Er wordt gebruikgemaakt van een `requests.Session` voor connection pooling, wat de overhead van het constant opzetten van nieuwe HTTPS-verbindingen minimaliseert.
•	**Dynamische Paginering**: De ISU API specificeert niet het totaal aantal pagina's. De scraper haalt batches van pagina's parallel op en stopt pas wanneer een API-call een lege lijst teruggeeft. Dit garandeert dat alle evenementen worden verzameld.
•	**Robuuste Foutafhandeling**: De `safe_get_json`-functie implementeert een retry-mechanisme met exponential backoff. Mislukte pogingen worden gelogd, wat het debuggen van API-problemen vereenvoudigt.
•	**Datafiltering**: Competities met "Team", "Mass" of "Mixed" in de titel worden direct gefilterd om alleen individuele afstanden te verwerken.

### 3.2. Fase 2: Transform (Dataverrijking en -transformatie)
In deze fase wordt de ruwe data omgezet naar bruikbare informatie. Dit gebeurt in vier substappen.

#### Transformatie 1: Toevoegen van Unieke Skater IDs (`skaterid_scraper.py`)
De ruwe data bevat alleen namen van schaatsers, die kunnen variëren en dubbelzinnig zijn. Dit script lost dat op door elke unieke schaatser te koppelen aan een stabiele, numerieke ID.
•	**Probleem**: Zonder een unieke ID is het onmogelijk om de prestaties van een individuele atleet betrouwbaar over meerdere seizoenen te volgen.
•	**Oplossing**: Het script koppelt elke `(naam, land)` combinatie aan een unieke ID van `speedskatingresults.com`.
    1.  **Efficiëntie**: Voordat API-requests worden gedaan, worden alle unieke `(naam, land)`-paren uit de dataset gehaald. Dit voorkomt duizenden onnodige, dubbele API-calls.
    2.  **Slimme Matching**: Voor elke unieke schaatser wordt eerst gezocht op de volledige achternaam. Als dit geen resultaat oplevert, wordt een tweede, flexibelere zoekopdracht uitgevoerd met alleen de eerste vier letters van de achternaam.
    3.  **Accuraatheid**: De API-resultaten worden gevalideerd met een `SequenceMatcher`. Een ID wordt alleen toegekend als de voornaam uit de API voor meer dan 90% overeenkomt met de voornaam in de brondata, wat zorgt voor een hoge betrouwbaarheid.

#### Transformatie 2: Toevoegen van Seizoensbeste Tijd (`seasonalbest_scraper.py`)
Een enkele wedstrijdtijd is lastig te interpreteren zonder context. Dit script voegt een cruciale prestatie-benchmark toe.
•	**Probleem**: De absolute eindtijd van een rit geeft geen indicatie van de vorm van de schaatser.
•	**Oplossing**: Voor elke rit haalt het script, gebruikmakend van de zojuist toegevoegde `SkaterID`, de beste tijd van die schaatser op die afstand uit het *voorgaande* seizoen op.
    1.  **Contextuele Data**: Dit levert een `SeasonalBest`-kolom op, die als baseline dient om de huidige prestatie tegen af te zetten.
    2.  **API-gebruik**: Het script berekent het voorgaande seizoen op basis van de wedstrijddatum en gebruikt de `SkaterID` om een gerichte API-call te doen naar `speedskatingresults.com`.

#### Transformatie 3: Weerdata Toevoegen (`add_weather_to_conditions_with_location.py`)
Dit script gebruikt de locatie- en datumgegevens om voor elke wedstrijd de historische weersomstandigheden op te halen.
•	**Probleem**: De Open-Meteo API is gevoelig voor rate limiting, vooral bij complexe queries (veel datapunten over een lange periode).
•	**Oplossing: Jaar-voor-Jaar Strategie**: Er is gekozen voor een defensieve en betrouwbare strategie. Data voor een locatie wordt opgesplitst in jaarlijkse batches. Het script vraagt data op voor één jaar, pauzeert een seconde, en gaat dan pas verder met het volgende jaar. Dit maximaliseert de kans op een succesvolle extractie.

#### Transformatie 4: TFM Berekening (`calculate_estimated_tfm.py`)
De laatste transformatiestap berekent de `EstimatedTFM` en `EstimatedTFMBuffer` met de formule: `(Startpaar - 1) * Interval`.
•	**Speciale Logica voor de 10.000m**: Bij de 10km vindt vaak halverwege een dweilpauze plaats. Het script houdt hier intelligent rekening mee:
    1.  Het aantal unieke startparen wordt geteld. Voor races met minder dan 8 paren wordt aangenomen dat er geen dweilpauze is.
    2.  Voor races met 8 of meer paren wordt aangenomen dat er halverwege een dweilpauze is.
    3.  Voor alle paren die na de pauze starten, wordt de TFM-berekening gereset, wat een veel accuratere schatting oplevert.

### 3.3. Fase 3: Load (Data-opslag)
De laatste stap, uitgevoerd door **`load_to_database.py`**, laadt de schone, verrijkte data in een gestructureerde database.
•	**Databasekeuze: SQLite**: Er is gekozen voor SQLite omdat het serverless is en de database in één lokaal bestand (`.db`) opslaat. Dit maakt het project zeer portable.
•	**Schema Creatie**: Het script leest de kolomnamen uit de CSV-bestanden, maakt deze SQL-compatibel en creëert automatisch de tabellen (`DROP TABLE IF EXISTS`). Alle kolommen worden gedefinieerd als `TEXT` voor maximale flexibiliteit.

## 4. Outputformaat en Verantwoording
•	**Formaat**: CSV (Comma-Separated Values) met een puntkomma (`;`) als scheidingsteken en UTF-8 encoding.
•	**Verantwoording**:
    - **Human-Readable**: CSV is direct leesbaar in teksteditors en spreadsheetsoftware.
    - **Machine-Readable**: Het gestructureerde formaat is eenvoudig in te lezen door databases, data-analyse tools (Pandas, R) en BI-software.
    - **Standaardisatie**: CSV is een universele de-facto standaard voor data-uitwisseling.

## 5. Aanbevelingen voor Toekomstige Versies
•	**Volledige Automatisering (Scheduling)**: Het `run_workflow.py` script kan periodiek worden ingepland met een scheduler zoals cron (Linux/macOS) of Taakplanner (Windows).
•	**Configuration management**: Hardgecodeerde waarden kunnen worden verplaatst naar een extern configuratiebestand (bijv. `config.ini` of `.env`).
•	**Uitgebreide monitoring en logging**: Implementeer een robuuster logging-systeem, bijvoorbeeld door output naar een centraal bestand te schrijven met timestamps en log-levels.
•	**Data kwaliteitschecks**: Bouw na elke stap geautomatiseerde controles in (bijv. op onverwachte NULL-waarden of incorrecte datatypes) om de betrouwbaarheid van de uiteindelijke dataset te verhogen.
