def parse_vhl_html(html, team_name):
    soup = BeautifulSoup(html, "html.parser")
    events = []

    for day in soup.select(".calendar-page__day"):
        date_text = day.select_one(".calendar-page__day-date").text.strip()
        matches = day.select(".calendar-page__match")

        for match in matches:
            home = match.select(".calendar-page__match-team--home .calendar-page__match-team-name")[0].text.strip()
            away = match.select(".calendar-page__match-team--guest .calendar-page__match-team-name")[0].text.strip()

            if team_name not in (home, away):
                continue

            score = match.select_one(".calendar-page__match-score_total")
            score_text = score.text.strip() if score else ""

            city = match.select_one(".calendar-page__match-city").text.strip()

            events.append({
                "date": date_text,
                "home": home,
                "away": away,
                "score": score_text,
                "city": city
            })

    return events
