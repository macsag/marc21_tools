from SPARQLWrapper import SPARQLWrapper, JSON

sparql = SPARQLWrapper("https://query.wikidata.org/sparql")

sparql.setQuery("""
SELECT ?entityLabel ?bnId ?entity
WHERE
{
    ?entity wdt:P1695 ?bnId .
    ?entity wdt:P21 ?gender .
    ?entity wdt:P569 ?dateOfBirth .
    SERVICE wikibase:label { bd:serviceParam wikibase:language "pl" }
} LIMIT 100
""")
sparql.setReturnFormat(JSON)
results = sparql.query().convert()

for result in results['results']['bindings']:
    print(result['bnId']['value'])
