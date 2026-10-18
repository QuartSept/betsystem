# Lig taraması (karar #47)

Oluşturulma: 2026-10-18T17:50:48+00:00 (UTC).

## Kurallar (ön kayıt)

- Sezonlar: 2019/20–2022/23. Model kurulmadı; yalnızca marjsız Pinnacle erken ve kapanış olasılıkları.
- Bilgi kazancı = log-loss(erken) − log-loss(kapanış), maç başına ortalama; bootstrap %95 GA.
- Uygunluk: en az 900 maçta erken ve kapanış birlikte dolu, doluluk ≥ %90.
- Seçim: Premier League dışındaki uygun ligler arasında bilgi kazancı en yüksek 2 lig. Marj, maç sayısı ve xG yalnızca bilgi içindir.

## Sonuç

Seçilen ligler: **B1 (Belçika Pro League), N1 (Hollanda Eredivisie)**.

## Lig tablosu (bilgi kazancına göre)

| lig | ad | maç | PS erken+kapanış | doluluk | xG (Understat) | bilgi kazancı | %95 GA | kapanış log-loss | kapanış marjı | erken marjı | uygun |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B1 | Belçika Pro League | 1150 | 1146 | 0.997 | yok | 0.0087 | 0.0036 … 0.0137 | 0.971 | 0.0359 | 0.0408 | True |
| N1 | Hollanda Eredivisie | 1150 | 1150 | 1.0 | yok | 0.0075 | 0.0030 … 0.0122 | 0.9221 | 0.0326 | 0.0329 | True |
| G1 | Yunanistan Super League | 960 | 922 | 0.96 | yok | 0.0068 | 0.0001 … 0.0135 | 0.9354 | 0.0493 | 0.0552 | True |
| SC1 | İskoçya Championship | 632 | 632 | 1.0 | yok | 0.0062 | -0.0007 … 0.0129 | 1.0581 | 0.0418 | 0.045 | False |
| SC3 | İskoçya League Two | 607 | 606 | 0.998 | yok | 0.0059 | -0.0015 … 0.0131 | 1.0025 | 0.0547 | 0.0623 | False |
| T1 | Türkiye Süper Lig | 1448 | 1414 | 0.977 | yok | 0.0058 | 0.0009 … 0.0106 | 0.9999 | 0.0324 | 0.0343 | True |
| F2 | Fransa Ligue 2 | 1420 | 1411 | 0.994 | yok | 0.0057 | 0.0013 … 0.0101 | 1.0337 | 0.0352 | 0.0388 | True |
| SC0 | İskoçya Premiership | 863 | 853 | 0.988 | yok | 0.0046 | -0.0008 … 0.0100 | 0.9146 | 0.0314 | 0.0314 | False |
| I2 | İtalya Serie B | 1520 | 1500 | 0.987 | yok | 0.0045 | 0.0005 … 0.0087 | 1.0468 | 0.0309 | 0.0314 | True |
| E2 | İngiltere League One | 2056 | 2040 | 0.992 | yok | 0.0041 | 0.0008 … 0.0072 | 1.0099 | 0.0347 | 0.0379 | True |
| E3 | İngiltere League Two | 2096 | 2081 | 0.993 | yok | 0.0037 | 0.0006 … 0.0067 | 1.053 | 0.0342 | 0.0374 | True |
| EC | İngiltere National League | 1986 | 1977 | 0.995 | yok | 0.0033 | -0.0008 … 0.0075 | 1.008 | 0.0452 | 0.0482 | True |
| SP2 | İspanya Segunda | 1848 | 1842 | 0.997 | yok | 0.0031 | -0.0013 … 0.0073 | 1.045 | 0.0321 | 0.0373 | True |
| E0 | İngiltere Premier League | 1520 | 1520 | 1.0 | var | 0.0031 | -0.0005 … 0.0067 | 0.967 | 0.0254 | 0.0267 | True |
| I1 | İtalya Serie A | 1520 | 1517 | 0.998 | var | 0.003 | -0.0009 … 0.0070 | 0.9597 | 0.0262 | 0.0275 | True |
| F1 | Fransa Ligue 1 | 1419 | 1417 | 0.999 | var | 0.0029 | -0.0010 … 0.0071 | 0.987 | 0.0258 | 0.0271 | True |
| D2 | Almanya 2. Bundesliga | 1224 | 1218 | 0.995 | yok | 0.0027 | -0.0016 … 0.0068 | 1.0445 | 0.0309 | 0.0317 | True |
| D1 | Almanya Bundesliga | 1224 | 1224 | 1.0 | var | 0.0024 | -0.0015 … 0.0063 | 0.9834 | 0.0261 | 0.0276 | True |
| SP1 | İspanya La Liga | 1520 | 1517 | 0.998 | var | 0.0022 | -0.0017 … 0.0060 | 0.9813 | 0.0258 | 0.0272 | True |
| SC2 | İskoçya League One | 609 | 606 | 0.995 | yok | 0.0016 | -0.0059 … 0.0093 | 0.9949 | 0.0543 | 0.0621 | False |
| P1 | Portekiz Primeira Liga | 1224 | 1222 | 0.998 | yok | 0.0007 | -0.0037 … 0.0053 | 0.9295 | 0.0323 | 0.0334 | True |
| E1 | İngiltere Championship | 2208 | 2204 | 0.998 | yok | 0.0003 | -0.0025 … 0.0031 | 1.0462 | 0.0297 | 0.0301 | True |

## Referans: Premier League Faz 3 modelinin hareket testi (karar #46)

1140 maç, eğim 0.0014 (tek yönlü %95 alt sınır -0.0178; %95 GA -0.0219 … 0.0246): **geçemedi**. Sonuç bazında korelasyon: H -0.022, D +0.069, A -0.005.
