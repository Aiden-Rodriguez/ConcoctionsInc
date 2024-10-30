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

def get_potion_quan(connection, reset_timestamp):
    result = connection.execute(sqlalchemy.text("""
                                                SELECT 
                                                potion_id,
                                                SUM(potion_quantity) AS quantity
                                                FROM ledger_transactions
                                                WHERE potion_id IS NOT NULL AND created_at >= :reset_timestamp
                                                GROUP BY potion_id
                                                HAVING SUM(potion_quantity) != 0
                                                """),
                                                {"reset_timestamp": reset_timestamp})
    return result.mappings().all()

def get_ml_quan(connection, reset_timestamp):
    result = connection.execute(sqlalchemy.text("""
                                                SELECT 
                                                SUM(red_ml_change) AS red,
                                                SUM(green_ml_change) AS green,
                                                SUM(blue_ml_change) AS blue,
                                                SUM(dark_ml_change) AS dark
                                                FROM ledger_transactions
                                                WHERE created_at >= :reset_timestamp
                                                """),
                                                {"reset_timestamp": reset_timestamp})
    row = result.mappings().one()
    red_ml = row['red']
    green_ml = row['green']
    blue_ml = row['blue']
    dark_ml = row['dark']
    return [red_ml, green_ml, blue_ml, dark_ml]

def get_gold_quan(connection, reset_timestamp):
    result = connection.execute(sqlalchemy.text("""
                                                SELECT 
                                                SUM(gold_difference)
                                                FROM ledger_transactions
                                                WHERE created_at >= :reset_timestamp
                                                """),
                                                {"reset_timestamp": reset_timestamp})
    return result.scalar()

@router.get("/audit")
def get_inventory():
    """ """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""SELECT
                                                    reset_timestamp
                                                    FROM global_inventory"""))
        reset_timestamp = result.scalar()

        gold = get_gold_quan(connection, reset_timestamp)
        ml_quans = get_ml_quan(connection, reset_timestamp)
        potion_quans = get_potion_quan(connection, reset_timestamp)

        num_potions = 0
        for potion in potion_quans:
            num_potions += potion['quantity']


        return {"number_of_potions": num_potions, "ml_in_barrels": ml_quans[0]+ml_quans[1]+ml_quans[2]+ml_quans[3], "gold": gold}

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

        result = connection.execute(sqlalchemy.text("""SELECT ml_capacity, potion_capacity, reset_timestamp
                                                    FROM global_inventory"""))
        row = result.mappings().one()
        
        ml_capacity = row['ml_capacity']
        potion_capacity = row['potion_capacity']
        reset_timestamp = row['reset_timestamp']

        gold = get_gold_quan(connection, reset_timestamp)
        ml_quans = get_ml_quan(connection, reset_timestamp)
        potion_quans = get_potion_quan(connection, reset_timestamp)

        num_potions = 0
        for potion in potion_quans:
            num_potions += potion['quantity']

        num_ml_total = ml_quans[0]+ml_quans[1]+ml_quans[2]+ml_quans[3]

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
            gold_change = 1000*(capacity_purchase.ml_capacity + capacity_purchase.potion_capacity)
            connection.execute(sqlalchemy.text("""INSERT INTO capacity_order_table (id, potion_capacity_purchased, ml_capacity_purchased)
                VALUES (:order_id, :potion_capacity_purchased, :ml_capacity_purchased)"""), 
                {"order_id": order_id, "potion_capacity_purchased": capacity_purchase.potion_capacity, "ml_capacity_purchased": capacity_purchase.ml_capacity})
            
            
            connection.execute(sqlalchemy.text("""UPDATE global_inventory
                                                        SET ml_capacity = ml_capacity + :ml_change, 
                                                        potion_capacity = potion_capacity + :potion_change
                                                        """),
                                                        {"ml_change": capacity_purchase.ml_capacity*10000, "potion_change": capacity_purchase.potion_capacity*50})
            
            connection.execute(sqlalchemy.text("""INSERT INTO ledger_transactions (exchange_type, linking_id, gold_difference)
                                               VALUES ('Capacity Upgrade', :id, :gold_diff)
                                               """),
                                               {"id": order_id, "gold_diff": -1*gold_change})

    return "OK"
