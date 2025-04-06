Central Coast Cauldrons is a stubbed out API meant to serve as a starting point for learning how to build backend servies that integrate with a persistance layer. You will progressively build out your own forked version of the API and integrate with a progressively more sophisticated database backend. When you register your backend at the [Potion Exchange](https://potion-exchange.vercel.app/) simulated customers will shop at your store using your API. 

The application's setting is a simulated fantasy RPG world with adventurers seeking to buy potions. You are one of many shops in this world that offer a variety (over 100k possibilities) of potions.

## Understanding the Game Mechanics

With an initial capital of 100 gold, no potions in your inventory, and devoid of barrels, your backend API is scheduled to be invoked at regular intervals, known as 'ticks' that go off every two hours. There are 12 ticks in a day, and 7 days in a week. The weekdays in the Potion Exchange world are:
1. Edgeday
1. Bloomday
1. Aracanaday
1. Hearthday
1. Crownday
1. Blesseday
1. Soulday

There are three primary actions that may unfold during these ticks:

1. **Customer Interactions**: On each tick, one or more simulated customers access your catalog endpoint intending to buy potions. The frequency and timing of customer visits vary based on the time of day, and each customer exhibits specific potion preferences. Your shop's performance is evaluated and scored based on multiple criteria (more details on [Potion Exchange](https://potion-exchange.vercel.app/)), which in turn influences the frequency of customer visits.

2. **Potion Creation**: Every alternate tick presents an opportunity to brew new potions. Each potion requires 100 ml of any combination of red, green, blue, or dark liquid. You must have sufficient volume of the chosen color in your barrelled inventory to brew a potion.

3. **Barrel Purchasing**: On every alternate tick, you have an opportunity to purchase additional barrels of various colors. Your API receives a catalog of barrels available for sale and should respond with your purchase decisions. The gold cost of each barrel is deducted from your balance upon purchase.

Part of the challenge in these interactions is you are responsible for keeping track of your gold and your various inventory levels. The [Potion Exchange](https://potion-exchange.vercel.app/) separately keeps an authoritiative record (which can be viewed under Shop stats).

### Customers
Customers of various types have different seasonality on when they show up. For example, some customers are more likely to shop on certain days of the week and at certain times of day. Customers each have their own class which has a huge impact on what types of potions that customer is looking for. The amount a customer is willing to spend on a given potion depends on both the customers own level of wealth and how precisely the potions available in a store match their own preference.

Lastly, customers are more likely to shop in a store in the first place that has a good reputation. You can see your shop's reputation with a particular class at [Potion Exchange](https://potion-exchange.vercel.app/). Reputation is based on three different factors:
1. Value: Value is based upon selling the cheapest potions to a given class compared to competitors. 
2. Quality: Quality is based upon selling potions that most closely match a customer's preferences.
3. Reliability: Reliability is based upon not having errors in the checkout process. Your site being down or offering up potions for sale you don't have in inventory are examples of errors that will hurt reliability.
4. Recognition: Recognition is based upon the number of total successful purchasing trips that customers of that class have had. The more you serve a particular class, the more others of that class will trust to come to you.

For more information please reference the [API Spec](APISpec.md)
