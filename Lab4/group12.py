from mable.cargo_bidding import TradingCompany, Bid

class Company12(TradingCompany):
    def __init__(self, fleet, name):
        super().__init__(fleet, name)
        self._future_trades = None
        # Maps each trade to the vessel and schedule we planned for it in inform()
        self._planned_schedules = {}



    #  Store information about trades that will appear in the next auction.
    def pre_inform(self, trades, time):
        print(f"pre_inform called: storing {len(trades)} upcoming trades for time {time}")
        self._future_trades = trades

    # Tentatively add the trade to this vessel's schedule.
    # Returns (True, new_schedule) if the resulting schedule is feasible, otherwise (False, None).
    def try_schedule_on_vessel(self, vessel, trade):
        try:
            new_schedule = vessel.schedule.copy()
            new_schedule.add_transportation(trade)

            if new_schedule.verify_schedule():
                return True, new_schedule

            print(
                f"Schedule not feasible for vessel {vessel.name} "
                f"with trade {getattr(trade, 'id', 'unknown')} (time-window/capacity/other)."
            )
            return False, None

        except Exception as e:
            print(f"Exception while trying schedule on vessel {vessel.name}: {e}")
            return False, None


    # Try all vessels and return the first (vessel, schedule) pair that yields a feasible schedule.
    # If none are feasible, return (None, None).
    def plan_for_trade(self, trade):
        for vessel in self._fleet:
            feasible, sched = self.try_schedule_on_vessel(vessel, trade)
            if feasible:
                return vessel, sched

        print(
            f"No feasible vessel found for trade "
            f"{getattr(trade, 'id', 'unknown')} – will NOT bid on this trade."
        )
        return None, None

    # Decide which trades to bid on in the current auction round.
    # Only bid on trades for which we can find at least one feasible vessel schedule.
    def inform(self, trades, *args, **kwargs):
        print(f"\ninform called: {len(trades)} trades offered this round")
        bids = []
        self._planned_schedules = {}

        for i, trade in enumerate(trades):
            try:
                origin = getattr(trade, "origin_port", getattr(trade, "start_port", None))
                destination = getattr(trade, "destination_port", getattr(trade, "end_port", None))

                print(
                    f"Trade {i}: origin={getattr(origin, 'name', origin)}, "
                    f"dest={getattr(destination, 'name', destination)}, "
                    f"amount={getattr(trade, 'amount', 'NA')}"
                )

                vessel, sched = self.plan_for_trade(trade)
                if vessel is None or sched is None:
                    continue
               
                self._planned_schedules[trade] = (vessel, sched)

                cost = self.predict_cost(vessel, trade)
                # preliminary agent: bid at our estimated cost
                bid_amount = cost*1.2 
                bids.append(Bid(amount=bid_amount, trade=trade))
                print(
                    f"Trade {i}: vessel={vessel.name}, "
                    f"bid={bid_amount}, cost_estimate={cost}"
                )

            except Exception as e:
                print(f"Failed to process trade {i}: {e}")

        print(f"Total bids prepared: {len(bids)}")
        return bids

    # Apply schedules for the trades we actually won in the auction.
    # Uses the plans computed earlier in inform(), with a fallback recomputation if needed.
    def receive(self, contracts, auction_ledger=None, *args, **kwargs):
        print(f"\nreceive called: {len(contracts)} contracts won")

        for i, contract in enumerate(contracts):
            trade = contract.trade
            planned = self._planned_schedules.get(trade, None)

            if planned is None:
                print(
                    f"No stored plan for trade {getattr(trade, 'id', 'unknown')} "
                    f"in receive(); recomputing schedule."
                )
                vessel, sched = self.plan_for_trade(trade)
                if vessel is None or sched is None:
                    print(
                        f"Even recomputed schedule is infeasible for trade "
                        f"{getattr(trade, 'id', 'unknown')}. Leaving it unscheduled."
                    )
                    continue
            else:
                vessel, sched = planned

            try:
                if not sched.verify_schedule():
                    print(
                        f"Planned schedule for trade {getattr(trade, 'id', 'unknown')} "
                        f"failed verify_schedule() in receive(). Skipping."
                    )
                    continue

                print(
                    f"Applying schedule for trade {getattr(trade, 'id', 'unknown')} "
                    f"to vessel {vessel.name}"
                )
                vessel.schedule = sched

            except Exception as e:
                print(
                    f"Exception while applying schedule for trade "
                    f"{getattr(trade, 'id', 'unknown')} on vessel {vessel.name}: {e}"
                )

        self._future_trades = None

    # Return a simple cost estimate for performing this trade with this vessel.
    # This is intentionally basic for the preliminary submission.
    def predict_cost(self, vessel, trade):
        try:
            origin = getattr(trade, "origin_port", getattr(trade, "start_port", "UNKNOWN"))
            destination = getattr(trade, "destination_port", getattr(trade, "end_port", "UNKNOWN"))
            origin_name = getattr(origin, "name", origin)
            dest_name = getattr(destination, "name", destination)

            total_cost = 1000.0  
            print(f"Predicted cost for trade {origin_name}->{dest_name}: {total_cost}")
            return total_cost

        except Exception as e:
            print(f"Failed to predict cost: {e}")
            # Return a large number to avoid accidentally underbidding when we are unsure
            return 10_000.0
