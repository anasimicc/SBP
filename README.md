# Analiza video igara na Steam platformi

**Autori:** Ana Simić (IN 15/2022), Minja Knežič (IN 25/2022)

## O projektu

Projekat se bavi analizom podataka o video igrama sa Steam platforme, sa ciljem da se kroz upite nad bazom podataka odgovori na pitanja relevantna za dve različite uloge: **game industry analyst** i **???** - od toga koji žanrovi ostvaruju najbolji odnos popularnosti i kvaliteta, preko uticaja cene na uspešnost igre, do karakteristika koje izdvajaju najpopularnije igre od ostatka tržišta.

### Skup podataka

- **Dataset:** Steam Games Dataset
- **Izvor:** Kaggle
- **Platforma:** Steam
- **Broj igara:** preko 122.000
- **Veličina:** `games.csv` ≈ 389 MB
- **Broj kolona:** 39
- **Periodično ažuriranje:** mesečno

### Semantika podataka

Najvažnija polja u skupu podataka:

| Polje | Opis |
|---|---|
| `app_id` | Jedinstveni identifikator igre |
| `name` | Naziv igre |
| `release_date` | Datum izlaska |
| `price` | Cena igre |
| `estimated_owners` | Procena broja vlasnika |
| `positive`, `negative` | Broj pozitivnih i negativnih ocena |
| `genres` | Žanrovi igre |
| `developers`, `publishers` | Naziv studija koji je razvio igru i izdavač |
| `tags` | Ključne reči |
| `peak_ccu` | Najveći broj istovremenih igrača |
| `platforms` | Podržani operativni sistemi |
| `supported_languages` | Podržani jezici |

---

### Logička šema baze podataka

<img width="447" height="639" alt="image" src="https://github.com/user-attachments/assets/80a3a46a-f323-480c-b368-baa94055e077" />

<img width="593" height="542" alt="image (1)" src="https://github.com/user-attachments/assets/6da2c80b-9e8a-408e-887c-8d8c316ae1bf" />


## Optimizacija upita

Pregled upita nad kolekcijom `steam_games`, sa merama pre i posle optimizacije.

### 1. Koji žanrovi igara imaju najveći Quality Score (indeks kvaliteta), definisan kao kombinacija prosečnog odnosa pozitivnih recenzija i prosečne Metacritic ocene, među igrama sa najmanje 1000 ukupnih recenzija?

**Inicijalni upit**

```js
[
  {
    $addFields: {
      total_reviews_initial: {
        $add: [
          "$reviews.positive",
          "$reviews.negative"
        ]
      }
    }
  },
  {
    $match: {
      total_reviews_initial: {
        $gte: 1000
      }
    }
  },
  {
    $unwind: "$genres"
  },
  {
    $addFields: {
      positive_ratio: {
        $cond: [
          {
            $gt: ["$reviews.positive", 0]
          },
          {
            $divide: [
              "$reviews.positive",
              {
                $add: [
                  "$reviews.positive",
                  "$reviews.negative"
                ]
              }
            ]
          },
          0
        ]
      }
    }
  },
  {
    $group: {
      _id: "$genres",
      avg_user_score: {
        $avg: "$reviews.user_score"
      },
      avg_metacritic: {
        $avg: "$reviews.metacritic_score"
      },
      avg_recommendations: {
        $avg: "$reviews.recommendations"
      },
      avg_positive_ratio: {
        $avg: "$positive_ratio"
      },
      games: {
        $sum: 1
      }
    }
  },
  {
    $project: {
      _id: 0,
      genre: "$_id",
      avg_positive_ratio: 1,
      avg_metacritic: 1,
      avg_recommendations: 1,
      games: 1,
      combined_score: {
        $add: [
          {
            $multiply: ["$avg_positive_ratio", 50]
          },
          {
            $multiply: ["$avg_metacritic", 0.5]
          }
        ]
      }
    }
  },
  {
    $sort: {
      combined_score: -1
    }
  }
]
```

**Explain pre optimizacije**

| Metrika | Vrednost |
|---|---|
| Execution time | 535 ms |
| Documents examined | 122611 |

**Optimizacija**

Dodato je polje `total_reviews` u svaki dokument da se ne bi računalo pri svakom upitu (*computed pattern*):

```js
[
  { $set: { total_reviews: { $add: ["$reviews.positive", "$reviews.negative"] } } }
]
```

Kreiran indeks:

```js
db.steam_games.createIndex(
  { total_reviews: 1 },
  {
    partialFilterExpression: {
      total_reviews: { $gte: 1000 }
    }
  }
)
```

Upit je zatim izmenjen da koristi novo polje.

**Novi upit**

```js
[
  {
    $match: {
      total_reviews: {
        $gte: 1000
      }
    }
  },
  {
    $unwind: "$genres"
  },
  {
    $addFields: {
      positive_ratio: {
        $cond: [
          {
            $gt: ["$reviews.positive", 0]
          },
          {
            $divide: [
              "$reviews.positive",
              "$total_reviews"
            ]
          },
          0
        ]
      }
    }
  },
  {
    $group: {
      _id: "$genres",
      avg_user_score: {
        $avg: "$reviews.user_score"
      },
      avg_metacritic: {
        $avg: "$reviews.metacritic_score"
      },
      avg_recommendations: {
        $avg: "$reviews.recommendations"
      },
      avg_positive_ratio: {
        $avg: "$positive_ratio"
      },
      games: {
        $sum: 1
      }
    }
  },
  {
    $project: {
      _id: 0,
      genre: "$_id",
      avg_positive_ratio: 1,
      avg_metacritic: 1,
      avg_recommendations: 1,
      games: 1,
      combined_score: {
        $add: [
          {
            $multiply: ["$avg_positive_ratio", 50]
          },
          {
            $multiply: ["$avg_metacritic", 0.5]
          }
        ]
      }
    }
  },
  {
    $sort: {
      combined_score: -1
    }
  }
]
```

**Explain posle optimizacije**

| Metrika | Vrednost |
|---|---|
| Execution time | 77 ms |
| Documents examined | 7206 |

**Prikaz rezultata**

<img width="1881" height="580" alt="prvi upit" src="https://github.com/user-attachments/assets/197a17f0-b460-4893-a15c-8f7f8c618623" />


---

### 2. Kako se indeks uspešnosti razlikuje između cenovnih kategorija u prvorangiranom žanru iz prethodnog pitanja, pri čemu je indeks uspešnosti definisan kao kombinacija prosečnog broja istovremenih igrača (Peak CCU) i prosečnog broja preporuka?

**Inicijalni upit**

```js
[
  {
    $addFields: {
      price_bucket: {
        $switch: {
          branches: [
            {
              case: {
                $eq: ["$price", 0]
              },
              then: "Free"
            },
            {
              case: {
                $lte: ["$price", 2]
              },
              then: "0-2"
            },
            {
              case: {
                $lte: ["$price", 4]
              },
              then: "2-4"
            },
            {
              case: {
                $lte: ["$price", 7]
              },
              then: "4-7"
            },
            {
              case: {
                $lte: ["$price", 12]
              },
              then: "7-12"
            },
            {
              case: {
                $lte: ["$price", 30]
              },
              then: "12-30"
            }
          ],
          default: "30+"
        }
      }
    }
  },
  {
    $unwind: "$genres"
  },
  {
    $group: {
      _id: {
        genre: "$genres",
        price_bucket: "$price_bucket"
      },
      avg_user_score: {
        $avg: "$reviews.user_score"
      },
      avg_recommendations: {
        $avg: "$reviews.recommendations"
      },
      avg_peak_ccu: {
        $avg: "$owners.peak_ccu"
      },
      count: {
        $sum: 1
      }
    }
  },
  {
    $project: {
      _id: 0,
      genre: "$_id.genre",
      price_bucket: "$_id.price_bucket",
      avg_recommendations: 1,
      avg_peak_ccu: 1,
      count: 1,
      success_score: {
        $add: [
          {
            $multiply: [
              {
                $divide: ["$avg_peak_ccu", 1000]
              },
              50
            ]
          },
          {
            $multiply: [
              {
                $divide: [
                  "$avg_recommendations",
                  10000
                ]
              },
              50
            ]
          }
        ]
      }
    }
  },
  {
    $match: {
      genre: "Adventure"
    }
  },
  {
    $sort: {
      success_score: -1
    }
  }
]
```

**Explain pre optimizacije**

| Metrika | Vrednost |
|---|---|
| Execution time | 1435 ms |
| Documents examined | 122611 |

**Optimizacija**

Ovaj upit suštinski mora da prođe kroz svaki dokument - indeks ovde ne pomaže.

- Pokušano je restrukturiranje upita ubacivanjem `$project` ranije u pipeline, kako bi se ranije izvukla samo potrebna polja, a ostala ne bi bila vučena kroz ceo upit - nije donelo stvarnu optimizaciju.
- Dodato je polje `price_bucket` u čitavu šemu:

```js
db.steam_games_optimized.updateMany(
  {},
  [
    {
      $set: {
        price_bucket: {
          $switch: {
            branches: [
              { case: { $eq: ["$price", 0] }, then: "Free" },
              { case: { $lte: ["$price", 2] }, then: "0-2" },
              { case: { $lte: ["$price", 4] }, then: "2-4" },
              { case: { $lte: ["$price", 7] }, then: "4-7" },
              { case: { $lte: ["$price", 12] }, then: "7-12" },
              { case: { $lte: ["$price", 30] }, then: "12-30" }
            ],
            default: "30+"
          }
        }
      }
    }
  ]
)
```

Dodat je i compound multikey indeks nad tim poljem:

```js
db.steam_games_optimized.createIndex({ genres: 1, price_bucket: 1 })
```

Upit je zatim ponovo rekonstruisan.

**Novi upit**

```js
[
  {
    $match: {
      genres: "Adventure"
    }
  },
  {
    $unwind: "$genres"
  },
  {
    $match: {
      genres: "Adventure"
    }
  },
  {
    $group: {
      _id: {
        genre: "$genres",
        price_bucket: "$price_bucket"
      },
      avg_recommendations: {
        $avg: "$reviews.recommendations"
      },
      avg_peak_ccu: {
        $avg: "$owners.peak_ccu"
      },
      count: {
        $sum: 1
      }
    }
  },
  {
    $project: {
      _id: 0,
      genre: "$_id.genre",
      price_bucket: "$_id.price_bucket",
      avg_recommendations: 1,
      avg_peak_ccu: 1,
      count: 1,
      success_score: {
        $add: [
          {
            $multiply: [
              {
                $divide: ["$avg_peak_ccu", 1000]
              },
              50
            ]
          },
          {
            $multiply: [
              {
                $divide: [
                  "$avg_recommendations",
                  10000
                ]
              },
              50
            ]
          }
        ]
      }
    }
  },
  {
    $sort: {
      success_score: -1
    }
  }
]
```

**Explain posle optimizacije**

| Metrika | Vrednost |
|---|---|
| Execution time | 424 ms |
| Documents examined | 122611 |

**Prikaz rezultata**

<img width="1866" height="579" alt="drugi upit" src="https://github.com/user-attachments/assets/e36e9ff8-8ea8-448f-a565-353128c3c71d" />


---

### 3. Koje kombinacije tagova najčešće karakterišu najpopularnije igre, pri čemu se popularnost meri brojem istovremenih igrača (Peak CCU >= 1000)?

**Inicijalni upit**

```js
[
  {
    $match: {
      "owners.peak_ccu": {
        $gte: 1000
      }
    }
  },
  {
    $project: {
      tags: 1,
      allTags: "$tags"
    }
  },
  {
    $unwind: "$tags"
  },
  {
    $unwind: "$allTags"
  },
  {
    $match: {
      $expr: {
        $lt: ["$tags", "$allTags"]
      }
    }
  },
  {
    $group: {
      _id: {
        tag1: "$tags",
        tag2: "$allTags"
      },
      count: {
        $sum: 1
      }
    }
  },
  {
    $sort: {
      count: -1
    }
  },
  {
    $limit: 10
  },
  {
    $addFields: {
      tag_pair: {
        $concat: ["$_id.tag1", " + ", "$_id.tag2"]
      }
    }
  },
  {
    $project: {
      _id: 0,
      tag_pair: {
        $concat: ["$_id.tag1", " + ", "$_id.tag2"]
      },
      count: 1
    }
  }
]
```

**Pre optimizacije**

| Metrika | Vrednost |
|---|---|
| Execution time | 879 ms |
| Documents examined | 122611 |

**Optimizacija**

Kreiran indeks:

```js

db.steam_games.createIndex(
  { "owners.peak_ccu": 1 },
  {
    partialFilterExpression: {
      "owners.peak_ccu": { $gte: 1000 }
    }
  }
)
```

**Novi upit**

```js
[
  {
    $match: {
      "owners.peak_ccu": {
        $gte: 1000
      }
    }
  },
  {
    $project: {
      tags: 1,
      allTags: "$tags"
    }
  },
  {
    $unwind: "$tags"
  },
  {
    $unwind: "$allTags"
  },
  {
    $match: {
      $expr: {
        $lt: ["$tags", "$allTags"]
      }
    }
  },
  {
    $group: {
      _id: {
        tag1: "$tags",
        tag2: "$allTags"
      },
      count: {
        $sum: 1
      }
    }
  },
  {
    $sort: {
      count: -1
    }
  },
  {
    $limit: 10
  },
  {
    $addFields: {
      tag_pair: {
        $concat: ["$_id.tag1", " + ", "$_id.tag2"]
      }
    }
  },
  {
    $project: {
      _id: 0,
      tag_pair: {
        $concat: ["$_id.tag1", " + ", "$_id.tag2"]
      },
      count: 1
    }
  }
]
```

**Explain posle optimizacije**

| Metrika | Vrednost |
|---|---|
| Execution time | 266 ms |
| Documents examined | 491 |

**Prikaz rezultata**

<img width="1833" height="578" alt="treci upit" src="https://github.com/user-attachments/assets/3c391fa3-8eee-459e-a739-7dde3267a0a5" />


---

### 4. Koji developeri najkonzistentnije proizvode uspešne igre, pri čemu se uspešnost definiše kombinacijom prosečne Metacritic ocene i prosečnog broja istovremenih igrača, uz penalizaciju varijabilnosti kvaliteta?

**Inicijalni upit**

```js
[
  {
    $unwind: "$developers"
  },
  {
    $group: {
      _id: "$developers",
      games: { $sum: 1 },
      avg_metacritic: {
        $avg: "$reviews.metacritic_score"
      },
      avg_peak_ccu: { $avg: "$owners.peak_ccu" },
      std_metacritic: {
        $stdDevPop: "$reviews.metacritic_score"
      }
    }
  },
  {
    $match: { games: { $gte: 5 } }
  },
  {
    $addFields: {
      consistency_score: {
        $subtract: [
          {
            $add: [
              "$avg_metacritic",
              { $divide: ["$avg_peak_ccu", 100] }
            ]
          },
          "$std_metacritic"
        ]
      }
    }
  },
  {
    $sort: { consistency_score: -1 }
  },
  {
    $limit: 10
  }
]
```

**Explain pre optimizacije**

| Metrika | Vrednost |
|---|---|
| Execution time | 851 ms |
| Documents examined | 122611 |

**Optimizacija**

Dodatne optimizacije nad postojećim upitom verovatno ne bi dovele do pomaka, pa je pristup promenjen - kreirana je zasebna kolekcija koja čuva statistike o developerima:

```js
db.steam_games_optimization.aggregate([
  { $unwind: "$developers" },
  {
    $group: {
      _id: "$developers",
      games: { $sum: 1 },
      avg_metacritic: { $avg: "$reviews.metacritic_score" },
      avg_peak_ccu: { $avg: "$owners.peak_ccu" },
      std_metacritic: { $stdDevPop: "$reviews.metacritic_score" }
    }
  },
  { $match: { games: { $gte: 5 } } },
  {
    $addFields: {
      consistency_score: {
        $subtract: [
          {
            $add: [
              "$avg_metacritic",
              { $divide: ["$avg_peak_ccu", 100] }
            ]
          },
          "$std_metacritic"
        ]
      }
    }
  },
  { $out: "developer_stats" }
])
```

Kreiran je indeks nad novom kolekcijom:

```js
db.developer_stats.createIndex({ consistency_score: -1 })
```

Finalni upit se izvršava nad novom kolekcijom:

```js
db.developer_stats.find().sort({ consistency_score: -1 })
```

> Napomena: ovaj pristup je nezgodan ako se podaci često ažuriraju, ali za ovaj slučaj je prihvatljiv.

**Explain posle optimizacije**

| Metrika | Vrednost |
|---|---|
| Execution time | 6 ms |
| Documents examined | 2978 |

**Prikaz rezultata**

<img width="1863" height="557" alt="cetvrti upit" src="https://github.com/user-attachments/assets/f91c31a5-84e1-406c-a157-ae1053c6edd3" />


---

### 5. Koje karakteristike razlikuju top 10% najpopularnijih igara od ostatka tržišta, posmatrano kroz prosečnu cenu, broj DLC-ova, Metacritic ocenu, broj jezika i CCU?

**Inicijalni upit**

```js
[
  {
    $sort: {
      "owners.peak_ccu": -1
    }
  },
  {
    $group: {
      _id: null,
      games: {
        $push: {
          app_id: "$app_id",
          name: "$name",
          price: "$price",
          dlc_count: "$dlc_count",
          peak_ccu: "$owners.peak_ccu",
          metacritic: "$reviews.metacritic_score",
          languages: "$supported_languages"
        }
      },
      total: { $sum: 1 }
    }
  },
  {
    $project: {
      top10_cutoff: {
        $floor: { $multiply: ["$total", 0.1] }
      },
      games: 1,
      total: 1
    }
  },
  {
    $unwind: {
      path: "$games",
      includeArrayIndex: "rank"
    }
  },
  {
    $addFields: {
      segment: {
        $cond: [
          { $lt: ["$rank", "$top10_cutoff"] },
          "TOP_10",
          "OTHER"
        ]
      }
    }
  },
  {
    $group: {
      _id: "$segment",
      avg_price: { $avg: "$games.price" },
      avg_dlc: { $avg: "$games.dlc_count" },
      avg_metacritic: {
        $avg: {
          $cond: [
            { $gt: ["$games.metacritic", 0] },
            "$games.metacritic",
            "$$REMOVE"
          ]
        }
      },
      games_with_metacritic: {
        $sum: {
          $cond: [
            { $gt: ["$games.metacritic", 0] },
            1,
            0
          ]
        }
      },
      avg_languages: {
        $avg: {
          $size: {
            $ifNull: ["$games.languages", []]
          }
        }
      },
      avg_ccu: { $avg: "$games.peak_ccu" },
      count: { $sum: 1 }
    }
  },
  {
    $project: {
      _id: 0,
      segment: "$_id",
      avg_price: 1,
      avg_dlc: 1,
      avg_metacritic: 1,
      games_with_metacritic: 1,
      avg_languages: 1,
      avg_ccu: 1,
      count: 1
    }
  }
]
```

**Pre optimizacije**

| Metrika | Vrednost |
|---|---|
| Execution time | 1102 ms |
| Documents examined | 122611 |

**Optimizacija**

Kreiran indeks:

```js
db.steam_games.createIndex({ "owners.peak_ccu": -1 })
```

Sa ovim indeksom nije dobijena skoro nikakva optimizacija — iako se vreme sortiranja smanjuje, vreme grupisanja raste (potrebno je pronaći podatke za svaku vrednost iz indeksa). Dobijene vrednosti: 1071 ms execution time i 122611 documents examined.

Pokušana je i druga struktura upita, koja je dala još goru situaciju.

Konačno je isproban sledeći pristup:

```js
// Izračunaj granicu jednom
const cutoff = db.steam_games_optimized.aggregate([
  {
    $group: {
      _id: null,
      total: { $sum: 1 }
    }
  }
]).toArray()[0].total * 0.1   //  12261.1 -> floor = 12261


// Dodaj rank svakom dokumentu 
db.steam_games_optimized.aggregate([
  { $sort: { "owners.peak_ccu": -1 } },
  {
    $setWindowFields: {
      sortBy: { "owners.peak_ccu": -1 },
      output: { rank: { $documentNumber: {} } }
    }
  },
  {
    $addFields: {
      popularity_segment: {
        $cond: [{ $lte: ["$rank", 12261] }, "TOP_10", "OTHER"]
      }
    }
  },
  { $merge: { into: "steam_games_optimized", whenMatched: "merge" } }
])
```

Kreiran je i indeks na novom polju (na kraju se ne iskorišćava u upitu, pa je zbog toga izbrisan):

```js
db.steam_games_optimization.createIndex({ popularity_segment: 1 })
```

Upit je zatim rekonstruisan.

**Novi upit**

```js
[
  {
    $group: {
      _id: "$popularity_segment",
      avg_price: { $avg: "$price" },
      avg_dlc: { $avg: "$dlc_count" },
      avg_metacritic: {
        $avg: {
          $cond: [
            {
              $gt: [
                "$reviews.metacritic_score",
                0
              ]
            },
            "$reviews.metacritic_score",
            "$$REMOVE"
          ]
        }
      },
      games_with_metacritic: {
        $sum: {
          $cond: [
            {
              $gt: [
                "$reviews.metacritic_score",
                0
              ]
            },
            1,
            0
          ]
        }
      },
      avg_languages: {
        $avg: {
          $size: {
            $ifNull: ["$supported_languages", []]
          }
        }
      },
      avg_ccu: { $avg: "$owners.peak_ccu" },
      count: { $sum: 1 }
    }
  },

  {
    $project: {
      _id: 0,
      segment: "$_id",
      avg_price: 1,
      avg_dlc: 1,
      avg_metacritic: 1,
      games_with_metacritic: 1,
      avg_languages: 1,
      avg_ccu: 1,
      count: 1
    }
  }
]
```

**Explain osle optimizacije**

| Metrika | Vrednost |
|---|---|
| Execution time | 594 ms |
| Documents examined | 122611 |

**Prikaz rezultata**

<img width="1065" height="136" alt="peti upit" src="https://github.com/user-attachments/assets/1d819bed-c5f1-4ae5-b203-230d6d75d4c4" />


---
## Prikaz rezultata optimizacija
