from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

#As a very basic initial logic, purchase a new small green potion barrel only if the number of potions 
#in inventory is less than 10. Always mix all available green ml if any exists. Offer up for sale in 
#the catalog only the amount of green potions that actually exist currently in inventory.

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    # interact with db

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_green_potions, num_green_ml, gold FROM global_inventory"))

    """ """
    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    #interact with db

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory"))
        # num_green_potions = result.mappings().one()['num_green_potions']
        # num_green_ml = result.mappings().one()['num_green_ml']
        gold = result.mappings().one()['gold']
        return gold
    #     for row in result:
    #         num_green_potions = row['num_green_potions']
    #         num_green_ml = row['num_green_ml']
    #         gold = row['gold']

        # if  less than 10 pots, buy a barrel
        # pretty sure 100ml = 1 pot ..?
        # if num_green_potions < 10 :
        #     if gold >= Barrel.price :
        #         #buy the barrel
        #         gold = gold - Barrel.price
        #         num_green_ml += Barrel.ml_per_barrel

        # #updating database with transaction
        # with db.engine.begin() as connection:
        #     connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = :100, gold = :50"))

    """ """

    # return [
    #     {
    #         "sku": "SMALL_GREEN_BARREL",
    #         "quantity": 1,
    #     }
    # ]

    # return [
    #     {
    #         "sku": "SMALL_RED_BARREL",
    #         "quantity": 1,
    #     }
    # ]