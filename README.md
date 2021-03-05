# Celebritrade
 A full-stack stock tweet notification service using Google NLP, BigQuery, MongoDB, Twilio, FMP API, and Twitter API, using a flask backend and bootstrap frontend.

# What it does
Celebritrade lets you: Subscribe to your favorite celebrities, market predictors, or stock gurus on Twitter.<br>
Opt-in for call+text or just text notifications when your celebrity's tweets has a potential to affect the market price for a company.<br>
Get latest information on stock prices for the respective companies, trending news articles, and tweet sentiment score, all in one place, guiding you to make a reasonable and rational decision.<br>
Unsubscribe from the service.<br>

# How it works
Celebritrade leverages a number of API's and Services which are - Google's BigQuery and Natural Language APIs, Twitter API, FinancialModellingPrep API, Twilio Programmable Voice API, and MongoDB. The frontend is a bootstrap site that lets you subscribe your number to celebrities by specifying their twitter @handles. Any changes to an ongoing subscription can be made through the same site. A POST request is made to the Flask backend hosted on Heroku where the subscription details make an update to our Twitter Streams Listener to include your celebrities. This is done with thread safety in mind as Twitter only allows one active Stream Listener for a developer account.<br>
When a tweet is caught, I run entity analysis on the Tweet to extract words that may refer to a company or stock. These candidate words are now searched against a massive NASDAQ listing through an SQL query on BigQuery. If there are hits, the corresponding ticker strings are returned. Contextual information about the price, and news articles are retrieved from calls to the FinancialModellingPrep API. This data is combined with a sentiment score of the Tweet, again retrieved from Google's Natural Language API, and delivered to the customer using Twilio via the desired notification method.<br>
All data surrounding client information and twitter subscriptions are stored using MongoDB which is the database I am most familiar with.
