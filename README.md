L'applicativo usa le API KEY di TMDB (The Movie Database) presentando una pagina iniziale con i film in tendenza. Se l'utente
scrive il titolo di un film nella casella di ricerca, è possibile ottenere una lista (parziale per motivi di performance) dei 
film il cui titolo contiene la parola inserita. Cliccando sul film, si ottiene una scheda del film con 
alcune informazioni, in basso appaiono 6 tra gli attori principali. Cliccando su un attore, è possibile visionare la 
scheda relativa a quell'attore. Se mancano le informazioni in italiano del film o dell'attore, queste vengono sostituite da
sommari in lingua inglese.

Le url sono protette in caso di manipolazione, infatti il sistema ridirige la pagina manipolata alla home page del sito. 
