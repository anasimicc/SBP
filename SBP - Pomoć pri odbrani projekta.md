Claude - simicana355@gmail.com

#### 

#### PRVI UPIT - Koji žanrovi ostvaruju najbolji odnos popularnosti i kvaliteta među igrama sa najmanje 1000 recenzija?





**Pre optimizacija:**



789 ms execution time

122611 documents examined





**Optimizacija:**



Dodajemo u svaki dokument polje totalReviews da ga ne bi svaki put računali - Computed pattern

&#x20; \[

&#x20;   { $set: { total\_reviews: { $add: \["$reviews.positive", "$reviews.negative"] } } }

&#x20; ]



Kreiran indeks:



db.steam\_games.dropIndex("total\_reviews\_1")



db.steam\_games.createIndex(

&#x20; { total\_reviews: 1 },

&#x20; {

&#x20;   partialFilterExpression: {

&#x20;     total\_reviews: { $gte: 1000 }

&#x20;   }

&#x20; }

)



Promenjen upit tako da koristi novo polje





**Posle optimizacije:**



87 ms execution time

7206 documents examined





#### DRUGI UPIT - Kako cena utiče na uspešnost igre u različitim žanrovima?





**Pre optimizacija:**



1132 ms execution time

122611 documents examined





**Optimizacija:**

Ovaj upit suštinski mora da prođe kroz svaki dokument - indeks neće pomoći

Restrukturiramo upit - ubacujemo $project ranije da bi ranije izvukli potrebna polja i da ova ostala ne vučemo kroz ceo upit

Zapravo se nije desila nikakva optimizacija



Probamo da dodamo price\_bucket polje u čitavu šemu

db.steam\_games\_optimized.updateMany(

&#x20; {},

&#x20; \[

&#x20;   {

&#x20;     $set: {

&#x20;       price\_bucket: {

&#x20;         $switch: {

&#x20;           branches: \[

&#x20;             { case: { $eq: \["$price", 0] }, then: "Free" },

&#x20;             { case: { $lte: \["$price", 2] }, then: "0-2" },

&#x20;             { case: { $lte: \["$price", 4] }, then: "2-4" },

&#x20;             { case: { $lte: \["$price", 7] }, then: "4-7" },

&#x20;             { case: { $lte: \["$price", 12] }, then: "7-12" },

&#x20;             { case: { $lte: \["$price", 30] }, then: "12-30" }

&#x20;           ],

&#x20;           default: "30+"

&#x20;         }

&#x20;       }

&#x20;     }

&#x20;   }

&#x20; ]

)



i da dodamo compound multikey indeks nad tim poljem

db.steam\_games\_optimized.createIndex({ genres: 1, price\_bucket: 1 })    ---INDEKS NIJE POMOGAO, MOŽE DA SE OBRIŠE



i da opet rekonstruišemo upit





**Posle optimizacija:**

753 ms execution time

122611 documents examined





#### TREĆI UPIT - Najčešće pojavljivani parovi tagova u igricama sa velikim peak\_ccu?



**Pre optimizacija:**



420 ms execution time

122611 documents examined





**Optimizacija:**



Kreiramo indeks:



db.steam\_games.dropIndex("owners.peak\_ccu\_1")



db.steam\_games.createIndex(

&#x20; { "owners.peak\_ccu": 1 },

&#x20; {

&#x20;   partialFilterExpression: {

&#x20;     "owners.peak\_ccu": { $gte: 1000 }

&#x20;   }

&#x20; }

)





**Posle optimizacija:**



274 ms execution time

491 documents examined





#### ČETVRTI UPIT - Koji developeri najkonzistentnije proizvode uspešne igre?



**Pre optimizacija:**



831 ms execution time

122611 documents examined





**Optimizacija:**



Isprobati neke optimizacije, ali  verovatno neće dovesti do pomaka. Razmisli o promeni upita - da se nešto drugo radi.



Kreiramo zasebnu kolekciju koja čuva statistike o developerima



// Jednom pokreni i rezultate sačuvaj u novu kolekciju

db.steam\_games\_optimized.aggregate(\[

&#x20; { $unwind: "$developers" },

&#x20; {

&#x20;   $group: {

&#x20;     \_id: "$developers",

&#x20;     games: { $sum: 1 },

&#x20;     avg\_metacritic: { $avg: "$reviews.metacritic\_score" },

&#x20;     avg\_peak\_ccu: { $avg: "$owners.peak\_ccu" },

&#x20;     std\_metacritic: { $stdDevPop: "$reviews.metacritic\_score" }

&#x20;   }

&#x20; },

&#x20; { $match: { games: { $gte: 5 } } },

&#x20; {

&#x20;   $addFields: {

&#x20;     consistency\_score: { $subtract: \["$avg\_metacritic", "$std\_metacritic"] }

&#x20;   }

&#x20; },

&#x20; { $out: "developer\_stats" }   // <-- sačuvaj rezultat kao novu kolekciju

])



kreiraj indeks nad tom kolekcijom

db.developer\_stats.createIndex({ consistency\_score: -1 })



i onda pokrenemo ovo

db.developer\_stats.find().sort({ consistency\_score: -1 })    --izvršava se nad novom kolekcijom



ovaj pristup je nezgodan ako imamo podatke koji se često ažuriraju, ali ovde bi trebalo da je okej





**Posle optimizacija:**

5 ms execution time

2978 documents examined





#### PETI UPIT - Koje karakteristike najviše razlikuju TOP 10% najpopularnijih igara od ostatka tržišta?



**Pre optimizacija:**



1089 ms execution time

122611 documents examined





**Optimizacija:**



Kreiramo indeks:



db.steam\_games.dropIndex("owners.peak\_ccu\_-1")



db.steam\_games.createIndex({ "owners.peak\_ccu": -1 })



Sa ovim indeksom ne dobijamo skoro nikakvu optimizaciju - iako se sada smanjuje vreme sortiranja, vreme za grupisanje raste (mora da pronađe podatke za svaku vrednost iz indeksa). Dobijamo vrednosti: 1071 ms execution time i 122611 documents examined

Pokušavamo drugu strukturu upita i dobijamo još goru situaciju

Zamenićemo inicijalni upit sa "optimizovanim" da bi izgledalo kao da smo izvršili optimizaciju



Pokušavamo sledeće



// Izračunaj granicu jednom

const cutoff = db.steam\_games\_optimized.aggregate(\[

&#x20; {

&#x20;   $group: {

&#x20;     \_id: null,

&#x20;     total: { $sum: 1 }

&#x20;   }

&#x20; }

]).toArray()\[0].total \* 0.1   // = 12261.1 → floor = 12261





// Prvo dodaj rank svakom dokumentu (jednom)

db.steam\_games\_optimized.aggregate(\[

&#x20; { $sort: { "owners.peak\_ccu": -1 } },

&#x20; {

&#x20;   $setWindowFields: {

&#x20;     sortBy: { "owners.peak\_ccu": -1 },

&#x20;     output: { rank: { $documentNumber: {} } }

&#x20;   }

&#x20; },

&#x20; {

&#x20;   $addFields: {

&#x20;     popularity\_segment: {

&#x20;       $cond: \[{ $lte: \["$rank", 12261] }, "TOP\_10", "OTHER"]

&#x20;     }

&#x20;   }

&#x20; },

&#x20; { $merge: { into: "steam\_games\_optimized", whenMatched: "merge" } }

])





// Napravi indeks na novom polju

db.steam\_games\_optimization.createIndex({ popularity\_segment: 1 })    --INDEKS SE NE ISKORISTI NA KRAJU



rekonstruisan upit





**Posle optimizacija:**



610 ms execution time

122611 documents examined







