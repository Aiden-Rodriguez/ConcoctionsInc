from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/audit")
def get_inventory():
    """ """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""SELECT num_green_ml,
                                                    num_blue_ml,
                                                    num_red_ml, 
                                                    num_dark_ml, 
                                                    gold 
                                                    FROM global_inventory"""))
        row = result.mappings().one()

        num_green_ml = row['num_green_ml']
        num_blue_ml = row['num_blue_ml']
        num_red_ml = row['num_red_ml']
        num_dark_ml = row['num_dark_ml']
        num_ml = num_red_ml + num_blue_ml + num_green_ml + num_dark_ml
        gold = row['gold']

        result = connection.execute(sqlalchemy.text("""SELECT SUM(inventory)
                                                    FROM potion_info_table"""))
        num_potions = result.scalar()
        
        return {"number_of_potions": num_potions, "ml_in_barrels": num_ml, "gold": gold}


# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    #if potion amount is 40% of storage, buy upgrade
    #if ml amount is 40% of storage, buy upgrade
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""SELECT SUM(inventory)
                                                    FROM potion_info_table"""))
        num_potions = result.scalar()

        result = connection.execute(sqlalchemy.text("""SELECT ml_capacity, potion_capacity,
                                                    num_red_ml, num_green_ml,
                                                    num_blue_ml, num_dark_ml,
                                                    gold
                                                    FROM global_inventory"""))
        row = result.mappings().one()
        
        num_green_ml = row['num_green_ml']
        num_blue_ml = row['num_blue_ml']
        num_red_ml = row['num_red_ml']
        num_dark_ml = row['num_dark_ml']
        gold = row['gold']
        num_ml_total = num_red_ml + num_blue_ml + num_green_ml + num_dark_ml
        ml_capacity = row['ml_capacity']
        potion_capacity = row['potion_capacity']

        quan_potion_capacity = 0
        quan_ml_capacity = 0
        #prioritize potion space a bit
        if num_potions/potion_capacity >= 0.40 and gold >= 1000 and num_potions > 20:
            gold -= 1000
            quan_potion_capacity += 1
        if num_ml_total/ml_capacity >= 0.40 and gold >= 1000 and num_potions > 20:
            gold -= 1000
            quan_ml_capacity += 1

        return {
            "potion_capacity": quan_potion_capacity,
            "ml_capacity": quan_ml_capacity
        }

class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int

# Gets called once a day
@router.post("/deliver/{order_id}")
def deliver_capacity_plan(capacity_purchase : CapacityPurchase, order_id: int):
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""SELECT EXISTS
                                                    (SELECT 1 FROM capacity_order_table 
                                                    WHERE id = :order_id)"""), 
                                    {"order_id": order_id})
        #if the row exists, this transaction has already happened!! bad!
        row = result.scalar()

        #means transaction has already happened so dont make changes
        if row == True:
            return "OK"
        else:
            connection.execute(sqlalchemy.text("""INSERT INTO capacity_order_table (id, potion_capacity_purchased, ml_capacity_purchased)
                VALUES (:order_id, :potion_capacity_purchased, :ml_capacity_purchased)"""), 
                {"order_id": order_id, "potion_capacity_purchased": capacity_purchase.potion_capacity, "ml_capacity_purchased": capacity_purchase.ml_capacity})
            
            gold_change = 1000*(capacity_purchase.ml_capacity + capacity_purchase.potion_capacity)
            connection.execute(sqlalchemy.text("""UPDATE global_inventory
                                                        SET ml_capacity = ml_capacity + :ml_change, 
                                                        potion_capacity = potion_capacity + :potion_change,
                                                        gold = gold - :gold_change"""),
                                                        {"ml_change": capacity_purchase.ml_capacity*10000, "potion_change": capacity_purchase.potion_capacity*50, "gold_change": gold_change})

    return "OK"
