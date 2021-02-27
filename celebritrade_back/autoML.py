import os
from google.cloud import language_v1, bigquery


os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = ''


# Instantiates a client
client = language_v1.LanguageServiceClient()
query_client = bigquery.Client()
# The text to analyze
text = u"I kinda like Etsy"
type_ = language_v1.Document.Type.PLAIN_TEXT
text = text.replace("#","")
text = text.replace("$","")
# Optional. If not specified, the language is automatically detected.
# For list of supported languages:
# https://cloud.google.com/natural-language/docs/languages
language = "en"
document = {"content": text, "type_": type_, "language": language}

# Available values: NONE, UTF8, UTF16, UTF32
encoding_type = language_v1.EncodingType.UTF8

response = client.analyze_entities(request = {'document': document, 'encoding_type': encoding_type})
results = []
for entity in response.entities:
    print(u"Representative name for the entity: {}".format(entity.name))
    items = entity.name.split()
    block = {'STOCK','SHARE','HOLDINGS', 'COMMON', 'CORP','CORPORATION'}
    for item in items:
        if item.upper() not in block and language_v1.Entity.Type(entity.type_).name != "NUMBER":
        

            query_job = query_client.query(
                """
                SELECT Symbol, Name
                FROM `querytest-1611951823682.Stocks.Nasdaq` 
                WHERE UPPER(Name) like UPPER('{}')
                OR Symbol = UPPER('{}')
                LIMIT 5
                """.format('%'+item+' %', item)
            )
            query_results = query_job.result()
            results.append(query_results)
    # # Get entity type, e.g. PERSON, LOCATION, ADDRESS, NUMBER, et al
    # print(u"Entity type: {}".format(language_v1.Entity.Type(entity.type_).name))

    # # Get the salience score associated with the entity in the [0, 1.0] range
    # print(u"Salience score: {}".format(entity.salience))
for result in results:
    for row in result:
        print("{} : {} views".format(row.Symbol, row.Name)) 