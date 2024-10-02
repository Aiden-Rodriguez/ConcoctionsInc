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
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_green_ml, num_green_potions, num_red_ml, num_red_potions, num_blue_ml, num_blue_potions, num_dark_ml, num_dark_potions FROM global_inventory"))
        row = result.mappings().one()  # Using mappings to access the columns by name

        # Extract values from the row
        
        num_green_ml = row['num_green_ml']
        num_green_potions = row['num_green_potions']
        num_red_ml = row['num_red_ml']
        num_red_potions = row['num_red_potions']
        num_blue_ml = row['num_blue_ml']
        num_blue_potions = row['num_blue_potions']
        num_dark_ml = row['num_dark_ml']
        num_dark_potions = row['num_dark_potions']

        quan_g = num_green_potions
        quan_r = num_red_potions
        quan_b = num_blue_potions
        quan_d = num_dark_potions


        for potion in potions_delivered :
            if potion.potion_type == [0, 100, 0, 0] :
                quan_g = potion.quantity + num_green_potions
                num_green_ml = num_green_ml - 100*potion.quantity
            elif potion.potion_type == [100, 0, 0, 0] :
                quan_r = potion.quantity + num_red_potions
                num_red_ml = num_red_ml - 100*potion.quantity
            elif potion.potion_type == [0, 0, 100, 0] :
                quan_b = potion.quantity + num_blue_potions
                num_blue_ml = num_blue_ml - 100*potion.quantity
            elif potion.potion_type == [0, 0, 0, 100] :
                quan_d = potion.quantity + num_dark_potions
                num_dark_ml = num_dark_ml - 100*potion.quantity
        with db.engine.begin() as connection:
            connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = :num_green_ml, num_green_potions = :quan_g, num_red_ml = :num_red_ml, num_red_potions = :quan_r, num_blue_ml = :num_blue_ml, num_blue_potions = :quan_b, num_dark_ml = :num_dark_ml, num_dark_potions = :quan_d;"),
                                {"num_green_ml": num_green_ml, "quan_g": quan_g, "num_red_ml": num_red_ml, "quan_r": quan_r, "num_blue_ml": num_blue_ml, "quan_b": quan_b, "num_dark_ml": num_dark_ml, "quan_d": quan_d})
    return "OK"

#deal with adding dictionary stuff
def add_or_increment_item(item_list, new_item):
    for item in item_list:
        #check if the item with the same sku already exists
        if item['potion_type'] == new_item['potion_type']:
            #increment the quantity by the value of the new item
            item['quantity'] += new_item['quantity']
            return

    #if the item does not exist, add it to the list
    item_list.append(new_item)

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_green_ml, num_red_ml, num_blue_ml, num_dark_ml FROM global_inventory"))

        row = result.mappings().one()  # Using mappings to access the columns by name

        # Extract values from the row
        num_green_ml = row['num_green_ml']
        num_blue_ml = row['num_blue_ml']
        num_red_ml = row['num_red_ml']
        num_dark_ml = row['num_dark_ml']
        #implement support for many pots later
        potion_list = []
        green = [0,100,0,0]
        red = [100,0,0,0]
        blue = [0,0,100,0]
        dark = [0,0,0,100]

        #convert all into green pots
        while num_green_ml >= 100 :
            num_green_ml -= 100
            add_or_increment_item(potion_list, {'potion_type': green, 'quantity': 1})
        while num_red_ml >= 100 :
            num_red_ml -= 100
            add_or_increment_item(potion_list, {'potion_type': red, 'quantity': 1})
        while num_blue_ml >= 100 :
            num_blue_ml -= 100
            add_or_increment_item(potion_list, {'potion_type': blue, 'quantity': 1})
        while num_dark_ml >= 100 :
            num_dark_ml -= 100
            add_or_increment_item(potion_list, {'potion_type': dark, 'quantity': 1})

        return potion_list

if __name__ == "__main__":
    print(get_bottle_plan())