# Web Application Features

Write here what features you want me to implement in the Flask application.

## Instructions
- List the features you want
- Be as specific or general as you prefer
- I'll implement them step by step
- You can add/modify this file anytime

## Example format:
```
1. Feature name
   - Description of what it should do
   - Any specific requirements

2. Another feature
   - Details...
```

---
*Write your requirements below this line:*

Use sqlite database to store the data. We need to use user from some dropdown imput. what user is used we will show data for that user.
for user we define api keys, and system should use that and binance_futures_interface(already implemented in module) to get current open positions of profile. 
show open position info somewhere in table temporary for now. in end of page.
user should be able to add new lead portfolio/ remove lead. update positions of the lead trader. we will update manually for now. 
For every position of lead trader we will add coefficent that will help as calculate the position for 10usd deposit. and then we will calculate by reverse(true/false) value and coefficent of reverse trade the postion that should be in our portfolio. Here is example. lead trader has buy BTCUSDT size: 1 BTC. first coefficent for 10 usd is 0.01. this mean that we do 1*0.01 = 0.01btc for 10usd account. and then we have reverse True, and coefficent 5. this mean we will calculate for our portfolio 0.05 sell order. This should be shown in every row of position. 


In main dashboard we should see all lead traders and his positions, from there we should be able easy and quick modify positions.
actions with positions:
    remove position
    new position(it can be last row of every lead trader positions)
    modify. it should be quick in table. modify coeff, size.
    show 10usd size in seperate column, and in next column calculated trade.
    somewhere new reverse show coefficent of that lead trader.
    

--------------------------
round sizes and usd values to 3 digits after . in web page
for every lead trader need to have margin balance and copy balance, it is editible value, show in one row with reverse and coefficent. copy balance is 10 by default but it also editible.
in positions table need to have new column - suggested 10usd coef. System should calculate based on margin if it is defined and copy balance. for example margin balance is 1000, copy balance is 10. suggested coef is 0.01. if we change margin or copy balance this column will be updated. it is only usggestion for user. 
AS you understand 10usd we change to be dynamic. so let's use copy balance coef, copy balance size names.. 10 usd now is dynamic value and it is copy balance


--------------------------------
change order of columns, symbol, original position, size, suggested coeff, copy balance coeff, copy balance size, calculated trade.
for new position line also show suggested coeff.
in column of suggested coeff also show size in brackets if suggested coeff will be used. it is only info. 
Add table with sum of calculated trades. Need to sum all leads positions, for example if one has 10 buy BTCUSDT calculated trade, second has 5 sell BTCUSDT calculated trade, need to show 5 buy. And in same row show what we have actual in our positions. It should be easy to visually check what is difference of calculated values and our real portfolio
