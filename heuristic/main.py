# This file takes the decision variable result Z from the CPLEX program
# and creates milk-runs using nearest neighbour logic.

import pandas as pd
import simplejson as json

# Set up program parameters defined in the model

z_df: pd.DataFrame = pd.read_csv("warehouse_to_store_shipments_p_w_s_t.csv", names=['P', 'W', 'S', 'T', 'Value'])
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

cost_store_to_store = [
    [0, 1135.297318, 2827.932107, 2022.003956, 1834.121043, 3308.005441, 1104.536102, 2366.854453, 1283.160161, 1759.602228],
    [1135.297318, 0, 2313.114783, 1869.545399, 1288.914272, 2683.616962, 580.0862005, 1397.891269, 1667.393175, 625.8594091],
    [2827.932107, 2313.114783, 0, 984.9365462, 1044.796631, 530.7541804, 1853.105502, 1372.005831, 1918.462926, 2289.497762],
    [2022.003956, 1869.545399, 984.9365462, 0, 749.4664769, 1515.585695, 1298.653148, 1623.607095, 946.2557794, 2114.544868],
    [1834.121043, 1288.914272, 1044.796631, 749.4664769, 0, 1483.273407, 808.9499366, 921.9544457, 1249.199744, 1402.069898],
    [3308.005441, 2683.616962, 530.7541804, 1515.585695, 1483.273407, 0, 2283.002409, 1522.005256, 2447.61108, 2552.743622],
    [1104.536102, 580.0862005, 1853.105502, 1298.653148, 808.9499366, 2283.002409, 0, 1276.401191, 1149.478142, 1005.683847],
    [2366.854453, 1397.891269, 1372.005831, 1623.607095, 921.9544457, 1522.005256, 1276.401191, 0, 2134.127456, 1073.778376],
    [1283.160161, 1667.393175, 1918.462926, 946.2557794, 1249.199744, 2447.61108, 1149.478142, 2134.127456, 0, 2154.738963],
    [1759.602228, 625.8594091, 2289.497762, 2114.544868, 1402.069898, 2552.743622, 1005.683847, 1073.778376, 2154.738963, 0]]

warehouses_nearest_neighbours = {
    1: [1, 9, 7, 2, 5, 10, 4, 8, 3, 6],
    2: [8, 10, 5, 3, 6, 7, 2, 4, 9, 1]

}

cost_warehouse_to_store = [
    [170.2938637, 1283.160161, 2988.143236, 2165.294437, 2000.849819, 3471.901496, 1274.754878, 2535.389516, 1387.551801, 1903.785702],
    [2740.456166, 1992.636445, 640.7027392, 1302.689526, 926.984358, 733.4848328, 1659.186548, 794.7955712, 2106.181379, 1821.0162]]


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
    def __init__(self, store, amount, cost) -> None:
        super().__init__()
        self.store = store
        self.amount = amount
        self.cost = cost

    store: int
    amount: int
    cost: float


class CurrentLocation:

    def __init__(self, is_warehouse, location) -> None:
        super().__init__()
        self.is_warehouse = is_warehouse
        self.location = location

    is_warehouse: bool
    location: int


class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, AllRunsInTimeDuringPeriod):
            return {'time': obj.time, 'collection_of_runs': obj.collection_of_runs}
        if isinstance(obj, CollectionOfRuns):
            return {'warehouse': obj.warehouse, 'runs': obj.runs}
        if isinstance(obj, Shipment):
            return {'store': obj.store, 'amount': obj.amount, 'cost': obj.cost}
        if isinstance(obj, FinalResult):
            return {'all_runs_in_period_t': obj.all_runs_in_period_t, 'total_cost': obj.total_cost}
        return json.JSONEncoder.default(self, obj)


class FinalResult:

    all_runs_in_period_t = []
    total_cost = 0


def main():
    result = FinalResult()
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
                current_location = CurrentLocation(is_warehouse=True, location=warehouse)
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
                        if current_location.is_warehouse:
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
                        if current_location.is_warehouse:
                            cost = cost_warehouse_to_store[warehouse - 1][next_store - 1]
                        else:
                            cost = cost_store_to_store[current_location.location - 1][next_store - 1]
                        result.total_cost += cost
                        shipment = Shipment(next_store, current_truck_volume_usage, cost)
                        current_run.append(shipment)
                        current_location = CurrentLocation(is_warehouse=False, location=next_store)

                        # Reset the current variables to prepare for another run.
                        store_closest_to_current_location_index = len(current_nearest_neighbours)  # break out of while
                        # Do not increment store_closest_to_current_store_index
                    else:
                        # You have fulfilled the demand at this store, move onto the next one
                        current_truck_volume_usage -= num_to_ship
                        # If you are currently at the warehouse, use the cost from warehouse --> store, else store --> store
                        if current_location.is_warehouse:
                            cost = cost_warehouse_to_store[warehouse - 1][next_store - 1]
                        else:
                            cost = cost_store_to_store[current_location.location - 1][next_store - 1]
                        shipment = Shipment(next_store, num_to_ship, cost)
                        result.total_cost += cost
                        current_run.append(shipment)
                        satisfied_demand[next_store] += num_to_ship
                        current_location = CurrentLocation(is_warehouse=False, location=next_store)
                        # Replace the previous nearest neighbours with the current nearest neighbours
                        current_nearest_neighbours = stores_nearest_neighbours[next_store]
                        # Since we are starting again from a new store, set the index to 0 to exhaust all possibilities
                        store_closest_to_current_location_index = 0
                if len(current_run) > 0:
                    cost = cost_warehouse_to_store[warehouse - 1][current_location.location - 1]
                    result.total_cost += cost
                    shipment = Shipment(-1 * warehouse, 0, cost)
                    current_run.append(shipment)
                    # 2d arrays start initialized with an empty value,
                    # so rather than appending the first element, replace it.
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
        result.all_runs_in_period_t.append(all_runs_in_period_t)
    return result


# Useful for running Python programs
if __name__ == '__main__':
    # Run the main program
    res = main()
    # Output the result to a text file called Output.txt
    json_res = json.dumps(res, sort_keys=True, cls=ComplexEncoder)
    with open("milk_run_output.json", "w") as text_file:
        text_file.write(json_res)
