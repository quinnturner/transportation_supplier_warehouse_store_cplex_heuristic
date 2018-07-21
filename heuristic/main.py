# This file takes the decision variable result Z from the CPLEX program
# and creates milk-runs using nearest neighbour logic.

import pandas as pd
import simplejson as json

# Set up program parameters defined in the model

z_df: pd.DataFrame = pd.read_csv("z.csv", names=['P', 'W', 'S', 'T', 'Value'])
num_trucks_df = pd.read_csv("num_trucks.csv", names=['W', 'S', 'T', 'Value'])

truck_capacity = 40

stores_nearest_neighbours = {
    1: [7, 2, 9, 10, 5, 4, 8, 3, 6],
    2: [7, 10, 1, 5, 8, 9, 4, 3, 6],
    3: [6, 4, 5, 8, 7, 9, 10, 2, 1],
    4: [5, 9, 3, 7, 6, 8, 2, 1, 10],
    5: [4, 7, 8, 3, 9, 2, 10, 6, 1],
    6: [3, 5, 4, 8, 7, 9, 10, 2, 1],
    7: [2, 5, 10, 1, 9, 8, 4, 3, 6],
    8: [5, 10, 7, 3, 2, 6, 4, 9, 1],
    9: [4, 7, 5, 1, 2, 3, 8, 10, 6],
    10: [2, 7, 8, 5, 1, 4, 9, 3, 6],
}

warehouses_nearest_neighbours = {
    1: [1, 9, 7, 2, 5, 10, 4, 8, 3, 6],
    2: [8, 10, 5, 3, 6, 7, 2, 4, 9, 1]

}


class AllRunsInTimeDuringPeriod:

    def __init__(self, time) -> None:
        super().__init__()
        self.time = time
        self.collection_of_runs = []

    time: int
    collection_of_runs: []


class CollectionOfRuns(json.JSONEncoder):

    def __init__(self, warehouse) -> None:
        super().__init__()
        self.warehouse = warehouse
        self.runs = [[]]

    # Runs from warehouse
    warehouse: int
    runs: [[]]


class Shipment:

    def __init__(self, store, amount) -> None:
        super().__init__()
        self.store = store
        self.amount = amount

    store: int
    amount: int


class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, AllRunsInTimeDuringPeriod):
            return {'time': obj.time, 'collection_of_runs': obj.collection_of_runs}
        if isinstance(obj, CollectionOfRuns):
            return {'warehouse': obj.warehouse, 'runs': obj.runs}
        if isinstance(obj, Shipment):
            return {'store': obj.store, 'amount': obj.amount}
        return json.JSONEncoder.default(self, obj)


def main():
    result = []  # Collection of AllRunsInTimeDuringPeriod
    for t in range(1, 11):
        all_runs_in_period_t = AllRunsInTimeDuringPeriod(t)
        for warehouse in range(1, 3):
            satisfied_demand = {
                1: 0,
                2: 0,
                3: 0,
                4: 0,
                5: 0,
                6: 0,
                7: 0,
                8: 0,
                9: 0,
                10: 0
            }
            # Get the nearest neighbours for the current warehouse
            warehouse_nearest_neighbours = warehouses_nearest_neighbours[warehouse]
            warehouse_neighbour_index = 0
            # Set-up the collection of runs for this warehouse in this period.
            collection_of_runs = CollectionOfRuns(warehouse)
            while warehouse_neighbour_index < len(warehouse_nearest_neighbours):
                # Since you are currently at the warehouse, your nearest neighbours
                # are the nearest neighbours to the warehouse.
                # Later, once you move to a store, the current_nearest_neighbours will
                # be set to the current nearest neighbours at that store.
                current_nearest_neighbours = warehouse_nearest_neighbours
                store_closest_to_current_location_index = warehouse_neighbour_index
                # You have not shipped anything yet, so you have a full truck of products
                current_truck_volume_usage = truck_capacity
                current_run = []  # list of shipments

                while store_closest_to_current_location_index < len(current_nearest_neighbours):
                    # Get the closest store to the current location
                    next_store = current_nearest_neighbours[store_closest_to_current_location_index]
                    # Filter the main data source to this warehouse, store and time period
                    all_product_shipped_to_next_stop = z_df.query(
                        'W == ' + str(warehouse) + ' and S == ' + str(next_store) + ' and T == ' + str(t))
                    # The number of units to ship the sum of all demand minus the satisfied demand in this period
                    num_to_ship = all_product_shipped_to_next_stop['Value'].sum() - satisfied_demand[next_store]
                    # To account for floating point errors, avoid equalities.
                    if abs(num_to_ship) < 0.01:
                        if current_nearest_neighbours == warehouse_nearest_neighbours:
                            # break out of while, we want to increment the WH index since at the WH right now
                            store_closest_to_current_location_index = len(
                                current_nearest_neighbours)
                        else:
                            # If you don't have anything to ship, move onto the next store that might.
                            store_closest_to_current_location_index += 1
                    elif num_to_ship > current_truck_volume_usage:
                        # You have too much stuff to ship, you will have to return to the warehouse after delivering
                        # the rest of your load.
                        satisfied_demand[next_store] += current_truck_volume_usage
                        shipment = Shipment(next_store, current_truck_volume_usage)
                        current_run.append(shipment)
                        # 2d arrays start initialized with an empty value,
                        # so rather than appending the first element, replace it.

                        # Reset the current variables to prepare for another run.
                        store_closest_to_current_location_index = len(current_nearest_neighbours)  # break out of while
                        # Do not increment store_closest_to_current_store_index
                    else:
                        # You have fulfilled the demand at this store, move onto the next one
                        current_truck_volume_usage -= num_to_ship
                        shipment = Shipment(next_store, num_to_ship)
                        current_run.append(shipment)
                        satisfied_demand[next_store] += num_to_ship
                        # Replace the previous nearest neighbours with the current nearest neighbours
                        current_nearest_neighbours = stores_nearest_neighbours[next_store]
                        # Since we are starting again from a new store, set the index to 0 to exhaust all possibilities
                        store_closest_to_current_location_index = 0
                if len(current_run) > 0:
                    if len(collection_of_runs.runs) == 1 and len(collection_of_runs.runs[0]) == 0:
                        collection_of_runs.runs[0] = current_run
                    else:
                        collection_of_runs.runs.append(current_run)
                # You have just fulfilled the demand of the store closest to the warehouse that had unfilled demand,
                # so go to the next store
                warehouse_neighbour_index += 1
            # Add all runs in this period to a master collection for the period
            all_runs_in_period_t.collection_of_runs.append(collection_of_runs)
        # Add all runs across all periods to the final result
        result.append(all_runs_in_period_t)
    return result


# Useful for running Python programs
if __name__ == '__main__':
    # Run the main program
    res = main()
    # Output the result to a text file called Output.txt
    json_res = json.dumps(res, sort_keys=True, cls=ComplexEncoder)
    with open("Output.txt", "w") as text_file:
        text_file.write(json_res)
