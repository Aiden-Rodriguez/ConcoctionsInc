from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ """
    #print(f"potions delievered: {potions_delivered} order_id: {order_id}")
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_green_ml, num_green_potions FROM global_inventory"))
        row = result.mappings().one()  # Using mappings to access the columns by name

        # Extract values from the row
        
        num_green_ml = row['num_green_ml']
        num_green_potions = row['num_green_potions']

        for potion in potions_delivered :
            quan = potion.quantity + num_green_potions
            reduced_green_ml = num_green_ml - 100*potion.quantity
            if potion.potion_type == [0,100,0,0] :
                with db.engine.begin() as connection:
                    connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = :reduced_green_ml, num_green_potions = :quan;"),
                                        {"reduced_green_ml": num_green_ml, "quan": num_green_potions})
    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory"))

        row = result.mappings().one()  # Using mappings to access the columns by name

        # Extract values from the row
        num_green_ml = row['num_green_ml']
        num_to_convert = 0
        #implement support for many pots later
        potion_list = []
        # Each bottle has a quantity of what proportion of red, blue, and
        # green potion to add.
        # Expressed in integers from 1 to 100 that must sum up to 100.

        # Initial logic: bottle all barrels into green potions.

        #convert all into green pots
        while num_green_ml >= 100 :
            num_green_ml -= 100
            num_to_convert += 1

        if num_to_convert > 0:
            return [
                    {
                        "potion_type": [0, 100, 0, 0],
                        "quantity": num_to_convert,
                    }
            ]
        else :
            return []

if __name__ == "__main__":
    print(get_bottle_plan())