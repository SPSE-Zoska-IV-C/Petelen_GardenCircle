# 🌱 GardenCircle

Jednoduchá webová aplikácia pre milovníkov prírody a rastlín. Umožňuje:
- pridávať príspevky,
- komentovať,
- čítať články a novinky,
- v budúcnosti používať AI chatbota (teraz len placeholder).

## Školitel
  - Mgr. Kristián Kolčák

## Technológie
- Backend: Python (Flask)
- Frontend: HTML, CSS, JavaScript
- Databáza: SQLite (súbor sa vytvorí automaticky)

## Štruktúra projektu
- `backend/`
  - `main.py` – Flask entry point (spúšťací súbor)
  - `routes.py` – definície trás (API a stránky)
  - `database.py` – pripojenie k SQLite
  - `models.py` – vytvorenie schémy tabuliek (posts, comments)
- `templates/` – HTML šablóny (Jinja2)
- `static/` – CSS, JS, obrázky a statické dáta (`articles.json`)

## Spustenie lokálne
1) Nainštaluj závislosti (odporúčaný virtuálny environment):
```bash
pip install -r requirements.txt
```
2) Spusti aplikáciu:
```bash
python -m backend.main
```
3) Otvor v prehliadači `http://localhost:5000`

## Funkcionality
- Domov: zoznam príspevkov, formulár na pridanie príspevku
- Detail príspevku: zobrazenie komentárov a formulár na pridanie
- Články: ukážkové tipy načítané zo `static/articles.json`
- Novinky: živé správy z The Guardian – Environment RSS (`https://www.theguardian.com/environment/rss`), s cachovaním ~15 min.
- Chatbot: stránka s textom „Coming soon“
- Login as admin: /admin/login (password: admin)

## Poznámky
- Dáta sa ukladajú do `backend/gardencircle.db`.
- Endpointy pre príspevky a komentáre vracajú JSON a sú použité jednoduchými `fetch` požiadavkami na frontende.
- Novinky nevyžadujú žiadne API kľúče.
