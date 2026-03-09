# The Clutch Myth: What the Data Actually Says

## Hook

You remember the shot. Damian Lillard from the logo—the wave goodbye to OKC. LeBron's fadeaway over Iguodala. Kyrie's three in Oracle. Kawhi's bounce on the rim in Toronto. We've built an entire mythology around players who "rise to the moment"—who get *better* when it matters most. The narrative is seductive: some guys have it, some don't. Clutch is a skill.

Here's the uncomfortable part: the numbers don't back it up. **Clutch isn't a skill we measure—it's a story we tell about stars.**

We analyzed eight seasons of NBA data (2017-18 through 2024-25), defining "clutch" as the last five minutes when the score is within five points. Over 1,400 player-seasons, we asked a simple question: if you shot well in clutch situations this year, did you shoot well next year? The answer was a Pearson correlation of **0.074**—basically no relationship. That's not a typo. A player's clutch performance in one season tells you almost nothing about their clutch performance the next. It's barely more predictive than a coin flip.

So what *is* going on?

---

## Setup

Clutch is real in the sense that the moment exists. The last five minutes, score within five—that's when coaches draw up plays for their stars, when defenses tighten, when the crowd holds its breath. The NBA even tracks it. We used the league's official clutch numbers: true shooting percentage, field goals, assists, possessions—everything we needed to test whether "clutch" is a repeatable skill or something else entirely.

We're not the first to ask. Analytics types have been skeptical for years. But we wanted to go beyond the aggregate and look at the players fans actually mythologize: LeBron, Dame, Kyrie, Curry, Kawhi, Jimmy Butler, and a roster of 22 stars with "clutch" reputations. We also wanted to test the *why*—why do we believe in clutch if the data is so weak? The answers turned out to be more interesting than the question.

---

## Data

**The sample size is tiny.** The average player gets about 35 clutch possessions per season. Their total? Over 800. Clutch represents **3.7%** of a star's offensive workload. You're drawing conclusions about a skill from a handful of shots. That's not enough to separate signal from noise—and the year-over-year correlation proves it. When we plotted clutch TS% in year N against clutch TS% in year N+1, the scatter looked like a cloud. No pattern. No consistency. The comeback is always *sample size*. Exactly—and that's why we shouldn't call it a skill. ([Chart: Is Clutch Repeatable?](charts/year_over_year_scatter.png))

**The stars get worse, not better.** We compared clutch TS% to overall TS% for 22 reputation players. Nineteen of them shot *worse* in clutch than in their normal game. Jimmy Butler dropped 8 percentage points. Kawhi Leonard dropped 6. Devin Booker, Donovan Mitchell, Luka Dončić, Kevin Durant—all worse. The years we've called Dame the most clutch guard in the league, his clutch TS% has been *below* his overall mark. Only three (Chris Paul, Paul George, Shai Gilgeous-Alexander) were meaningfully better. ([Chart: Are Clutch Players Actually Better Under Pressure?](charts/clutch_vs_overall_ts.png))

**A lot of "clutch" is free throws.** When we stripped out free throws and looked only at field-goal efficiency, the picture got uglier. Joel Embiid's clutch TS% looks solid—until you realize 41% of his clutch points came from the line. Jimmy Butler, Paul George, Dame, Trae Young—all heavily FT-dependent. The "pure shot-maker" narrative doesn't hold. ([Chart: How Much of Clutch Scoring Is Actually Free Throws?](charts/ft_stripped.png))

**But the ball *does* go to the star.** Every single reputation player took on more offensive load in clutch time. Ja Morant's share of his team's shots more than doubled. Jimmy Butler's did too. Trae Young, Donovan Mitchell, De'Aaron Fox—all spiked 80% or more. The average star gets more clutch shots in one *game* than some role players get in a month—and we still call it a star skill. The star gets the ball. He takes the shot. We remember the makes. ([Chart: The Ball Always Goes to the Star](charts/usage_spike.png))

**Playoffs tell the same story.** We ran the same tests on eight seasons of playoff data. The year-over-year correlation for clutch TS% was **r = 0.15**—still weak, and not statistically significant (p = 0.32). The playoff sample is even smaller: ~12 clutch possessions per player vs. 35 in the regular season. Stars who appear in the playoffs shot worse in clutch there too. If "playoff pressure" were different, we'd expect a different signal. We don't.

---

## Wrinkle

So why does clutch *feel* real?

You might say the moment is different—pressure, defense, play-calling. Sure. But if the moment were really different, we'd see it in the numbers. We don't.

**Ball movement collapses.** We measured the assist-to-FGM ratio in clutch vs. overall. For 21 of 22 stars, it dropped—often by 30–40%. Chris Paul, one of the best passers ever, saw his ratio cut nearly in half. The offense becomes hero-ball. Isolation. One-on-one. That's not "clutch"—it's habit. The system breaks down, and the star is left to create. ([Chart: Ball Movement Collapses in Clutch](charts/ball_movement_collapse.png))

**Home court helps some, not others.** Kawhi Leonard shoots 11 percentage points better at home in clutch. Kyrie, Giannis, Westbrook—all better at home. But LeBron, Curry, Trae Young, and De'Aaron Fox are actually *worse* at home. The crowd giveth and taketh away. ([Chart: Does Clutch Travel?](charts/home_away_split.png))

**We forget the misses.** For the three most mythologized clutch players—LeBron, Kyrie, Dame—we calculated their clutch miss rate. LeBron misses 53% of his clutch shots. Kyrie misses 54%. Dame misses **60%**. Six out of ten. We remember the logo three. We forget the five that clanked. ([Chart: What Fans Forget](charts/miss_rate.png))

**The narrative is selective.** We ran the same tests on *everyone*—not just the 22 stars. Among reputation players, only 3 shot meaningfully better in clutch than overall. Among non-stars with at least 40 clutch games? **102 players** shot better. Gabe Vincent, Jamal Crawford, Chris Boucher, Derrick Favors—names you don't associate with "clutch"—all outperformed their normal efficiency when it mattered. And 17 non-stars showed *repeatable* clutch performance (r > 0.5 across seasons): Terance Mann, Jaren Jackson Jr., Ricky Rubio, Anfernee Simons, P.J. Tucker. P.J. Tucker had more repeatable clutch numbers across seasons than most of the 22 stars. We never hear about that. ([Chart: The Narrative Is Selective](charts/hidden_clutch.png)) Remember that 0.074? This is why. That 3.7% of possessions? It's not enough to be a skill—but it's enough to build a reputation. Clutch isn't a skill we measure; it's a story we tell about stars. The data is full of "hidden clutch" players. The mythology ignores them.

**They don't choke on the ball.** If pressure hurt, we'd expect more turnovers. We found the opposite: 19 of 22 stars turn it over *less* in clutch than in their normal game. Chris Paul, Westbrook, Durant, LeBron—all protect the ball better when it matters. The TS% drop isn't panic or sloppiness. It's the shots. They just miss more. ([Chart: Stars Protect the Ball Better in Clutch](charts/turnover_rate.png))

**Survivorship bias, defensive attention, era effects**—all of it matters. Players who choke get benched. Stars face tighter D in clutch. The game has changed since 2017. We're not saying those shots don't matter, or that pressure isn't real. We're saying the idea that some guys "have it" and others don't doesn't survive the data. We're not claiming the numbers are perfect. We're claiming they're *enough* to question the myth.

---

## The One Who Fits the Myth

Of the 22 reputation players we tracked, only three shot meaningfully *better* in clutch than overall: Chris Paul, Paul George, and Shai Gilgeous-Alexander. Chris Paul isn’t just in that group—he’s the only one whose clutch edge is both large and built on more than free throws.

Across eight seasons, Paul’s clutch true shooting is **63.5%** versus **58.3%** overall—a **+5.2 percentage point** bump when it matters. Paul George (+2.5) and SGA (+1.3) improve too, but CP3’s gap is the biggest. And unlike many “clutch” names, only **31%** of his clutch points come from the line; his FT-stripped efficiency in clutch (55%) is still above his overall TS%. He’s not propping up the number with late-game foul hunting.

He also protects the ball better in clutch: his turnover rate drops from **14.4%** of possessions overall to **8.1%** in clutch—one of the largest improvements among the 22 stars. So when the game tightens, he’s both more efficient and more secure. Home/road splits fit the same story: **66.1%** clutch TS at home, **60.7%** on the road. The sample is still small enough that we shouldn’t overstate it—but if one star has a statistical case for “clutch” as a real, repeatable edge, it’s him. ([Chart: The Exception — Stars Who Shoot Better in Clutch](charts/clutch_exception_three.png))

---

## The Run That Fits: Tyrese Haliburton 2024-25

Tyrese Haliburton's 2024-25 playoff run was called one of the clutchest we've seen. The numbers back it up—for that run. His clutch true shooting in the playoffs was **59.8%** versus **58.1%** overall—a **+1.7 percentage point** bump when it mattered. Eleven clutch games, 37 points on 27 FGA and 9 FTA. He shot better in clutch than in his normal playoff game. That's real.

Here's the wrinkle: the year before, in the 2023-24 playoffs, Haliburton's clutch TS% was **32.8%**—vs. 62.6% overall. He was *29 percentage points worse* in clutch. Five games, 15 shots. Tiny sample. Noise. But it's the same player, one year apart: 32.8% clutch one playoffs, 59.8% the next. That's not repeatability. That's variance.

The hypothesis isn't "nobody ever shoots well in clutch." It's that clutch performance doesn't *repeat* year-over-year. Haliburton had one great run. If he does it again in 2025-26, we'll have two data points. Until then, 2024-25 stands as a case study: one run can build a narrative. If he regresses next playoffs, we'll forget this one.

---

## Verdict

So here's the real answer: clutch *moments* are real; clutch *reputations* are mostly built on a few makes we remember and a lot of misses we don't.

Clutch, as a repeatable shooting skill, doesn't hold up. The sample is too small. The year-over-year signal is too weak. The stars shoot worse, not better—and when they don't, a lot of it is free throws. What we call "clutch" is mostly volume, visibility, and memory. The ball goes to the star. He shoots. We remember the ones that go in.

A few players *did* show consistent clutch performance across seasons: Jayson Tatum (r = 0.85), Nikola Jokić (r = 0.73), Anthony Edwards (r = 0.87). Small samples, so we shouldn't overstate it—but if anyone has a case for repeatable clutch, it's them. Chris Paul is the one star who was genuinely *better* in clutch than overall. Everyone else? The myth is doing a lot of work.

Next time you hear "he's a clutch player," ask: better at what? Taking the shot—or making it?
