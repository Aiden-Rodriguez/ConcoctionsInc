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
    print("CALLED post_deliver_bottles()")

    red_deduction = green_deduction = blue_deduction = dark_deduction = 0
    for potion in potions_delivered:
        red = potion.potion_type[0]
        green = potion.potion_type[1]
        blue = potion.potion_type[2]
        dark = potion.potion_type[3]

        with db.engine.begin() as connection:
            result = connection.execute(sqlalchemy.text("""UPDATE potions
                                                        SET num_potions = num_potions + :quantity
                                                        WHERE parts_red = :red
                                                        AND parts_green = :green
                                                        AND parts_blue = :blue
                                                        AND parts_dark = :dark"""), 
                                                        [{"quantity": potion.quantity, "red": red, 
                                                          "green": green, 
                                                          "blue": blue, 
                                                          "dark": dark}])
        red_deduction += red * potion.quantity
        green_deduction += green * potion.quantity
        blue_deduction += blue * potion.quantity
        dark_deduction += dark * potion.quantity
        
    
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""UPDATE global_inventory 
                                                    SET num_red_ml = num_red_ml - :red, 
                                                    num_green_ml = num_green_ml - :green, 
                                                    num_blue_ml = num_blue_ml - :blue,
                                                    num_dark_ml = num_dark_ml - :dark"""),
                                                    [{"red": red_deduction, 
                                                      "green": green_deduction,
                                                      "blue": blue_deduction,
                                                      "dark": dark_deduction}])

    print(f"potions delievered: {potions_delivered} order_id: {order_id}")

    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: bottle all barrels into red potions.
    print("CALLED get_bottle_plan()")

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""SELECT SUM(li.gold) as gold, 
                                                    SUM(li.num_red_ml) as red_ml, 
                                                    SUM(li.num_green_ml) as green_ml, 
                                                    SUM(li.num_blue_ml) as blue_ml, 
                                                    SUM(li.num_dark_ml) as dark_ml
                                                    FROM ledgerized_inventory as li"""))
    ml_row = result.fetchone()

    red_ml = ml_row.red_ml
    green_ml = ml_row.green_ml
    blue_ml = ml_row.blue_ml
    dark_ml = ml_row.dark_ml

    print(f"red_ml: {red_ml}, green_ml: {green_ml}, blue_ml: {blue_ml}, dark_ml: {dark_ml}")

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""SELECT potion_capacity
                                                    FROM shop_states"""))
    row = result.fetchone()

    potion_cap = row.potion_capacity

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""SELECT sku, parts_red, parts_green, parts_blue, parts_dark
                                                    FROM potions_catalog 
                                                    ORDER BY priority ASC"""))
    potion_catalog = result.all()

    print("potion_catalog: ", potion_catalog)

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""SELECT pi.sku as sku, SUM(num_potions) as num_potions
                                                    FROM potions_inventory as pi
                                                    GROUP BY pi.sku"""))
    potion_inventory = result.fetchall()

    print("potion_inventory:", potion_inventory)

    available_space = potion_cap
    num_per_type = {}
    for row in potion_inventory:
        available_space -= row.num_potions
        num_per_type[row.sku] = row.num_potions

    # idea: I want to prioritize making special potions first
    # Notes:
    # - Paladins like purple potions
    temp_bottle_plan = []
    for potion in potion_catalog:
        temp_bottle_plan.append(0)

    again = True
    while available_space > 0 and again == True:
        again = False
        for i in range(len(potion_catalog)):
            if red_ml >= potion_catalog[i].parts_red and green_ml >= potion_catalog[i].parts_green and blue_ml >= potion_catalog[i].parts_blue and dark_ml >= potion_catalog[i].parts_dark and num_per_type[potion_catalog[i].sku] < (potion_cap // 4):
                temp_bottle_plan[i] += 1

                red_ml -= potion_catalog[i].parts_red
                green_ml -= potion_catalog[i].parts_green
                blue_ml -= potion_catalog[i].parts_blue
                dark_ml -= potion_catalog[i].parts_dark

                available_space -= 1
                num_per_type[potion_catalog[i].sku] += 1
                again = True
    
    bottle_plan = []
    for i in range(len(potion_catalog)):
        if temp_bottle_plan[i] > 0:
            bottle_plan.append({"potion_type": [potion_catalog[i].parts_red, potion_catalog[i].parts_green, potion_catalog[i].parts_blue, potion_catalog[i].parts_dark], "quantity": temp_bottle_plan[i]})

    print("temp_bottle_plan: ", temp_bottle_plan) 
    print("bottle_plan: ", bottle_plan)
    return bottle_plan


if __name__ == "__main__":
    print(get_bottle_plan())