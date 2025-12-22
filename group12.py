# group12.py
from collections import defaultdict, deque
import statistics

from mable.cargo_bidding import TradingCompany, Bid


class Company12(TradingCompany):
    def __init__(self, fleet, name):
        super().__init__(fleet, name)

        self.upcoming = None

        self.vessel_plan = {}
        self.trade_to_vessel = {}

        self.fudge = 1.15
        self.safe_profit = 0.02

        self.lane_prices = defaultdict(lambda: deque(maxlen=30))
        self.ratio_hist = deque(maxlen=60)
        self.ratio_floor = 1.04
        self.ratio_cap = 1.25
        self.undercut = 0.985

        self.min_cap = 20
        self.cap_mult = 8
        self.per_vessel_limit = 2

        self._cost_cache = {}

        self.debug = False
        self.debug_n = 6

    def pre_inform(self, trades, time):
        self.upcoming = trades
        if self.debug:
            print(f"pre_inform: {len(trades)} trades stored at {time}")

    def _trade_key(self, trade):
        o = getattr(trade, "origin_port", getattr(trade, "start_port", None))
        d = getattr(trade, "destination_port", getattr(trade, "end_port", None))
        o_name = getattr(o, "name", str(o))
        d_name = getattr(d, "name", str(d))

        amt = float(getattr(trade, "amount", 0.0))
        if amt <= 20000:
            bucket = "0-20k"
        elif amt <= 40000:
            bucket = "20-40k"
        elif amt <= 70000:
            bucket = "40-70k"
        else:
            bucket = "70k+"

        return (o_name, d_name, bucket)

    def _lane_median(self, trade):
        hist = self.lane_prices.get(self._trade_key(trade))
        if not hist:
            return None
        return statistics.median(hist)

    def _global_ratio(self):
        if not self.ratio_hist:
            return None
        r = statistics.median(self.ratio_hist)
        if r < self.ratio_floor:
            r = self.ratio_floor
        if r > self.ratio_cap:
            r = self.ratio_cap
        return r

    def _trade_id(self, trade):
        return getattr(trade, "id", id(trade))

    def _cost(self, vessel, trade):
        k = (id(vessel), self._trade_id(trade))
        if k in self._cost_cache:
            return self._cost_cache[k]
        c = self.predict_cost(vessel, trade)
        self._cost_cache[k] = c
        return c

    def predict_cost(self, vessel, trade):
        try:
            o = getattr(trade, "origin_port", getattr(trade, "start_port", "UNKNOWN"))
            d = getattr(trade, "destination_port", getattr(trade, "end_port", "UNKNOWN"))
            amt = float(getattr(trade, "amount", 0.0))

            dist = 0.0
            if o not in (None, "UNKNOWN") and d not in (None, "UNKNOWN"):
                for fn in ("distance", "distance_to", "great_circle_distance"):
                    f = getattr(o, fn, None)
                    if callable(f):
                        try:
                            dist = float(f(d))
                            break
                        except Exception:
                            pass

            base = 600.0
            per_unit = 0.055
            per_nm = 0.32

            return base + per_unit * amt + per_nm * dist
        except Exception:
            return 10_000.0

    def try_schedule_on_vessel(self, vessel, trade, base=None):
        try:
            s = base.copy() if base is not None else vessel.schedule.copy()
            s.add_transportation(trade)
            if s.verify_schedule():
                return True, s
            return False, None
        except Exception:
            return False, None

    def plan_for_trade(self, trade):
        best = None
        for v in self._fleet:
            ok, s = self.try_schedule_on_vessel(v, trade)
            if not ok:
                continue
            c = self._cost(v, trade)
            if best is None or c < best[0]:
                best = (c, v, s)
        if best is None:
            return None, None
        return best[1], best[2]

    def _fallback_margin(self, trade):
        amt = float(getattr(trade, "amount", 0.0))
        m = 0.08
        if amt > 70000:
            m += 0.03
        elif amt > 40000:
            m += 0.01
        else:
            m -= 0.02
        if m < 0.06:
            m = 0.06
        if m > 0.25:
            m = 0.25
        return m

    def _bid(self, trade, cost_fudged):
        base = cost_fudged * (1.0 + self._fallback_margin(trade))

        lane = self._lane_median(trade)
        g = self._global_ratio()

        options = [base]
        if lane is not None:
            options.append(lane * self.undercut)
        if g is not None:
            options.append(cost_fudged * g * self.undercut)

        bid = min(options)
        floor = cost_fudged * (1.0 + self.safe_profit)
        if bid < floor:
            bid = floor
        return bid

    def _cap(self):
        return max(self.min_cap, len(self._fleet) * self.cap_mult)

    def _order_key(self, trade):
        for attr in ("pickup_time", "start_time", "earliest_pickup", "time", "release_time"):
            if hasattr(trade, attr):
                try:
                    return float(getattr(trade, attr))
                except Exception:
                    pass
        return float(getattr(trade, "amount", 0.0))

    def inform(self, trades, *args, **kwargs):
        self.vessel_plan = {}
        self.trade_to_vessel = {}
        self._cost_cache = {}

        cap = self._cap()

        candidates = []
        use_count = defaultdict(int)

        for i, t in enumerate(trades):
            v, _ = self.plan_for_trade(t)
            if v is None:
                continue

            if use_count[id(v)] >= self.per_vessel_limit:
                continue
            use_count[id(v)] += 1

            raw = self._cost(v, t)
            cf = raw * self.fudge
            b = self._bid(t, cf)

            candidates.append((b, t, v))

            if self.debug and i < self.debug_n:
                print(f"cand: {v.name} cost={raw:.1f} bid={b:.1f}")

        candidates.sort(key=lambda x: x[0])
        candidates = candidates[:cap]

        by_vessel = defaultdict(list)
        for b, t, v in candidates:
            by_vessel[v].append((b, t))

        final = []
        for v, items in by_vessel.items():
            items.sort(key=lambda x: self._order_key(x[1]))

            base = v.schedule.copy()
            kept = []

            for b, t in items:
                ok, ns = self.try_schedule_on_vessel(v, t, base=base)
                if not ok:
                    continue
                base = ns
                kept.append((b, t))

            if kept:
                self.vessel_plan[v] = base
                for b, t in kept:
                    self.trade_to_vessel[t] = v
                    final.append((b, t))

        final.sort(key=lambda x: x[0])
        return [Bid(amount=b, trade=t) for b, t in final]

    def receive(self, contracts, auction_ledger=None, *args, **kwargs):
        if auction_ledger is not None:
            self._update_market(auction_ledger)

        touched = set()
        for c in contracts:
            v = self.trade_to_vessel.get(c.trade)
            if v is not None:
                touched.add(v)

        for v in touched:
            s = self.vessel_plan.get(v)
            if s is None:
                continue
            try:
                if s.verify_schedule():
                    v.schedule = s
            except Exception:
                pass

        self.upcoming = None

    def _update_market(self, auction_ledger):
        entries = []
        if isinstance(auction_ledger, (list, tuple)):
            entries = auction_ledger
        elif isinstance(auction_ledger, dict):
            for k in ("auctions", "entries", "ledger"):
                v = auction_ledger.get(k)
                if isinstance(v, (list, tuple)):
                    entries = v
                    break

        for e in entries:
            if not isinstance(e, dict):
                continue

            t = e.get("trade")
            if t is None:
                continue

            price = None
            for k in ("second_price", "clearing_price", "winning_price", "payment", "price"):
                if k in e and e[k] is not None:
                    try:
                        price = float(e[k])
                        break
                    except Exception:
                        pass
            if price is None:
                continue

            self.lane_prices[self._trade_key(t)].append(price)

            v, _ = self.plan_for_trade(t)
            if v is None:
                continue
            cf = self._cost(v, t) * self.fudge
            if cf > 1e-6:
                self.ratio_hist.append(price / cf)
