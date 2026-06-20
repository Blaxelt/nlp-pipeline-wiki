DIR=$(dirname "$0")

QUERY=$(<"$DIR"/request.txt)

# Compared to the legacy script, the API endpoint is now https://databus.dbpedia.org/sparql 
# and we directly specify the Accept header to get the response in the desired format. 
# We also use tail to skip the header line and sed to remove angle brackets from the URLs (different response format). 
DOWNLOADURLS=$(curl -sSf -H "Accept: text/tab-separated-values" -X POST \
  --data-urlencode "query=$QUERY" \
  "https://databus.dbpedia.org/sparql" \
  | tail -n +2 \
  | sed 's/[<>]//g')

echo "$DOWNLOADURLS" > new_output.txt