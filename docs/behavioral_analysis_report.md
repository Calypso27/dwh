# Rapport d'analyse comportementale

> **Portée de ce rapport.** Les données analysées proviennent des pages
> Facebook **BBC et CNN** (6-14 juillet 2017, 99,3 % anglophone). Elles ne
> décrivent **pas** l'audience de l'Institut Saint-Jean. Ce corpus sert de
> **substitut méthodologique** : il a exactement la structure attendue
> (commentaires rattachés à leur publication), ce qui permet de construire et
> d'éprouver la chaîne d'analyse. Aucun chiffre ci-dessous ne doit être cité
> comme un résultat portant sur l'école.

Rapport généré automatiquement par `python manage.py report-behavior`.
Toute valeur est reproductible en relançant la commande.

## 1. Périmètre

- Commentaires analysés : **47,899**, tous rattachés à leur publication
- Publications : **500** | Auteurs distincts : **33,868**
- Thèmes représentés : **15**
- Période : du 06/07/2017 au 14/07/2017

## 2. Réactivité : à quelle vitesse le public réagit

- Délai médian entre publication et commentaire : **0.97 h**
- 9 commentaires sur 10 arrivent en moins de **13.2 h**
- **50.5 %** des réactions surviennent dans l'heure, **77.9 %** dans les six heures

L'essentiel de la réaction se joue donc le jour même : une publication
qui n'a pas suscité de commentaire dans les six heures n'en suscitera
quasiment plus. C'est une contrainte directe sur le rythme de modération.

## 3. Segmentation comportementale des auteurs

| Segment | Auteurs | Part des auteurs | Commentaires | Part du volume | Délai médian | Longueur moy. | Thèmes/auteur |
|---|---:|---:|---:|---:|---:|---:|---:|
| ponctuel | 27,483 | 81.1 % | 27,483 | 57.4 % | 1.22 h | 184 car. | 1.00 |
| occasionnel | 3,758 | 11.1 % | 7,516 | 15.7 % | 1.52 h | 215 car. | 1.75 |
| regulier | 1,797 | 5.3 % | 5,933 | 12.4 % | 0.97 h | 224 car. | 2.55 |
| engage | 642 | 1.9 % | 3,952 | 8.3 % | 0.86 h | 261 car. | 3.94 |
| hyperactif | 188 | 0.6 % | 3,015 | 6.3 % | 0.56 h | 289 car. | 7.03 |

**Lecture.** 2.5 % des auteurs (segments *engagé* et *hyperactif*) produisent 14.5 % des commentaires. Une poignée de voix pèse donc lourdement sur la tonalité perçue d'une page — ignorer cette concentration conduirait à confondre l'opinion d'une minorité active avec celle du public.

## 4. Réaction selon le thème de la publication

C'est la réponse directe à « il faut regarder les commentaires par rapport
au post qui est associé ». Le thème provient de `config/taxonomy.yaml`.

| Thème | Publications | Commentaires | Commentaires/post | Délai médian | Longueur moy. |
|---|---:|---:|---:|---:|---:|
| politique_gouvernement | 80 | 7,975 | 99.7 | 0.55 h | 273 car. |
| affaire_russe | 27 | 2,691 | 99.7 | 0.77 h | 318 car. |
| justice_police | 30 | 2,936 | 97.9 | 0.87 h | 214 car. |
| solidarite | 13 | 1,137 | 87.5 | 0.89 h | 123 car. |
| sport | 9 | 806 | 89.6 | 0.98 h | 110 car. |
| culture_science | 24 | 2,252 | 93.8 | 1.01 h | 162 car. |
| sante | 20 | 1,882 | 94.1 | 1.06 h | 207 car. |
| faits_divers | 17 | 1,627 | 95.7 | 1.11 h | 145 car. |
| societe_famille | 50 | 4,916 | 98.3 | 1.23 h | 209 car. |
| non_classe | 141 | 13,382 | 94.9 | 1.25 h | 177 car. |
| conflit_international | 43 | 3,988 | 92.7 | 1.29 h | 196 car. |
| technologie | 11 | 1,027 | 93.4 | 1.73 h | 158 car. |
| environnement_climat | 7 | 647 | 92.4 | 1.89 h | 152 car. |
| economie_entreprise | 17 | 1,572 | 92.5 | 1.91 h | 203 car. |
| transport_aviation | 11 | 1,061 | 96.5 | 2.44 h | 163 car. |

**Lecture.** Le thème *politique_gouvernement* déclenche les réactions les plus rapides (0.55 h de délai médian), tandis que *affaire_russe* suscite les commentaires les plus longs (318 caractères en moyenne). Le sujet d'une publication ne change donc pas seulement le volume de réactions, mais leur nature.

## 5. Effet du format de la publication

| Format | Publications | Commentaires | Commentaires/post | Délai médian |
|---|---:|---:|---:|---:|
| texte | 336 | 31,803 | 94.7 | 0.92 h |
| video | 157 | 15,456 | 98.4 | 1.11 h |
| photo | 7 | 640 | 91.4 | 0.66 h |

## 6. Comparaison des deux pages

| Page | Publications | Commentaires | Auteurs | Délai médian | Longueur moy. |
|---|---:|---:|---:|---:|---:|
| BBC | 250 | 23,936 | 18,357 | 1.36 h | 187 car. |
| CNN | 250 | 23,963 | 15,935 | 0.69 h | 230 car. |

**424 auteurs commentent sur les deux pages** : les audiences se recouvrent partiellement. C'est le schéma d'analyse qui servira à comparer l'Institut à un établissement concurrent.

## 7. Rythme d'usage sur la journée

- Pic d'activité à **16 h** (2,981 commentaires)
- Creux à **8 h** (1,402 commentaires)
- Amplitude pic/creux : **×2.1**

## 8. Limites

- **Fenêtre de 8 jours** : aucune analyse de tendance ou de saisonnalité n'est possible. Les variations de volume quotidien reflètent la collecte, pas le comportement.
- **La colonne `commentaires/post` est plafonnée** : la source ne conserve au maximum que 100 commentaires par publication (médiane observée : 100). Tous les thèmes se retrouvent donc tassés entre 87 et 100, et cet indicateur ne mesure **pas** la popularité d'un sujet. Les comparaisons valides portent sur le **délai de réaction** et la **longueur des commentaires**, qui ne subissent pas ce plafond.
- **Couverture thématique partielle** : les publications sans mot-clé reconnu restent étiquetées `non_classe`. Beaucoup sont des accroches très courtes qui ne portent aucun sujet ; les classer de force fabriquerait du bruit.
- **Aucune donnée alumni** : le corpus ne contient aucun attribut de profil, les auteurs étant des pseudonymes hachés. Cet axe reste ouvert.
- **Corpus anglophone** : un modèle de sentiment entraîné ici ne se transposera pas tel quel au français.

