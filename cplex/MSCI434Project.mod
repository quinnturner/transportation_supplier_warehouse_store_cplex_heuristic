/*********************************************
 * OPL 12.7.1.0 Model
 * Author: Pallavi, Pia, Liam and Quinn
 * Creation Date: Jun 23, 2018 at 3:55:44 PM
 *********************************************/

// SOURCES:
// For equivalent ceiling contraint in linear format: https://www.ibm.com/developerworks/community/forums/html/topic?id=6648b68c-3ab9-453e-9380-81a0acc7c24f

 // Generic parameters
range BINARY = 0..1;
float epsilon = 0.00000001;
int M = 10000;		// sufficiently large number

/// Ranges
range I = 1..3;		// suppliers
range W = 1..2;		// warehouses
range S = 1..10;	// stores
range P = 1..5;		// products
range T = 1..10;	// days

// Imported from .dat file:
float forecastedDemand[P][S][T]  = ...;
float distances[S][W] = ...;
int fixedCostPerTruck = ...;
int costPerKm = ...;
int truckCapacity = ...;
int warehouseCapacities[W] = ...;
float warehouseHoldingCosts[W][P] = ...;
int supplierCostPerPallet[I][P] = ...;
int supplierMinOrderSize[I] = ...;
int fixedCostFromSupplierToWarehouse = ...;

// Decision variables
dvar int+ R[P][I][W][T] in BINARY; // Whether a product (p) is shipped from supplier (i) to warehouse (w) in period (t)
dvar float+ X[P][I][W][T]; // Number of products (p) shipped from supplier (i) to warehouse (w) in period (t)
dvar int+ Y[P][W][S] in BINARY; // Whether a product (p) is shipped from warehouse (w) to store (s)
dvar float+ Z[P][W][S][T]; // Number of products (p) shipped from warehouse (w) to store (s) in period (t)
dvar int+ NumTrucks[W][S][T]; // Because ceil(Z) is a non-linear operation, we must an equivalent linear approach to compute ceilings.

// There aren't true decision variables.
// Rather, they are used to clearly see the result in the problem browser.
dvar float+ costOfGoods;
dvar float+ whHoldingCost[P][W][T];
dvar float+ fixedCostTotal;
dvar float+ varTransCostTotal;
dvar float+ fcFromSupToWh;

minimize(
  costOfGoods +
  sum (p in P, w in W, t in T)(whHoldingCost[p][w][t]) + // Warehouse holding costs
  varTransCostTotal +
  fixedCostTotal + 
  fcFromSupToWh);

// Constraints
subject to {
	// These constraints are objective function terms.
	// However, to easily determine the results of these terms, we make them constraints.
	// The resulting decision variable values are shown in the problem browser in CPLEX.
	sum(p in P, i in I, w in W, t in T)(supplierCostPerPallet[i][p]*X[p][i][w][t]) == costOfGoods;
	sum(p in P, i in I, w in W, t in T)(fixedCostFromSupplierToWarehouse*R[p][i][w][t]) == fcFromSupToWh;
	sum(w in W, s in S, t in T)(fixedCostPerTruck*NumTrucks[w][s][t]) == fixedCostTotal;
	sum(w in W, s in S, t in T)(2*costPerKm*distances[s][w]*NumTrucks[w][s][t]) == varTransCostTotal;
	forall(p in P, w in W, t in T) sum(tCurrent in 1..t)((sum(i in I) X[p][i][w][tCurrent])-(sum(s in S) Z[p][w][s][tCurrent])) == whHoldingCost[p][w][t];
	
	// Warehouse-store sole sourcing
	forall(p in P, s in S) sum(w in W) Y[p][w][s] == 1;
	// Supplier min order
	forall (p in P, w in W, i in I, t in T) (X[p][i][w][t] - R[p][i][w][t]*supplierMinOrderSize[i]) >= 0;
	forall (p in P, w in W, i in I, t in T) (X[p][i][w][t] - R[p][i][w][t]*M) <= 0;
	// For an alternative model that allows the minimum order quantity to be divisible across
	// warehouses within a period, comment out the above two constraints and uncomment the below two constraints
	//forall (p in P, i in I, t in T) sum(w in W) (X[p][i][w][t] - R[p][i][w][t]*supplierMinOrderSize[i]) >= 0;
	//forall (p in P, i in I, t in T) sum(w in W) (X[p][i][w][t] - R[p][i][w][t]*M) <= 0;
	// Warehouse capacity
	forall (p in P, w in W, t in T) ((sum(i in I) X[p][i][w][t]) - (sum(s in S) Z[p][w][s][t])) <= warehouseCapacities[w];
	// Supplier to warehouse product transportation
	forall(p in P, w in W, t in T) sum(tCurrent in 1..t)((sum(i in I) X[p][i][w][tCurrent])-(sum(s in S) Z[p][w][s][tCurrent])) >= 0;
	// Demand at stores
	forall (p in P, s in S, t in T) sum(w in W) (Z[p][w][s][t] - Y[p][w][s]*forecastedDemand[p][s][t]) >= 0;
	// Equivalent contraints to performing a ceil() operation. Used to calculate NumTrucks.
	forall(w in W, s in S, t in T) NumTrucks[w][s][t] - (sum(p in P) Z[p][w][s][t])/truckCapacity <= 1 - epsilon;
	forall(w in W, s in S, t in T) (sum(p in P) Z[p][w][s][t])/truckCapacity - NumTrucks[w][s][t] <= 0;
}
