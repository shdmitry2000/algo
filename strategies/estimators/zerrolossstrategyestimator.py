import pandas as pd

from tda.tddataprovider import tdclientOptionshelper
from filters.phase2strat1.spread_math import apply_spread_cap


class StrategyEstimatorZerroloss_TD(tdclientOptionshelper):
    def __init__(self,symbol,shifts=[1],tdconsumer_key=None):
        self.symbol=symbol
        self.shifts=shifts
        super(tdclientOptionshelper, self).__init__(tdconsumer_key)
        # self.fee=tdclientOptionshelper.getFee()

    def getTDSingleOptionsDF(self,tdmarket_data):
        '''return options chain as dataframe'''
        ret = []

        for date in tdmarket_data['callExpDateMap']:
            for strike in tdmarket_data['callExpDateMap'][date]:
                ret.extend(tdmarket_data['callExpDateMap'][date][strike])
        for date in tdmarket_data['putExpDateMap']:
            for strike in tdmarket_data['putExpDateMap'][date]:
                ret.extend(tdmarket_data['putExpDateMap'][date][strike])

        df = pd.DataFrame(ret)

        # return df[['putCall', 'symbol','strikePrice','mark','daysToExpiration','intrinsicValue','theoreticalOptionValue','bid','ask','bidSize','askSize','totalVolume','volatility','delta','gamma','theta','vega','rho','openInterest','timeValue','percentChange','markChange']]
        return df[
            ['putCall', 'symbol', 'strikePrice', 'mark', 'daysToExpiration', 'intrinsicValue', 'theoreticalOptionValue',
             'percentChange', 'markChange','bid','ask']]




    def getStrategyFlatDataClened(self,tdmarket_data):

        dfcalls = tdmarket_data.loc[(tdmarket_data.putCall == 'CALL') & (tdmarket_data['mark'] != 0) & (tdmarket_data['bid'] != 0) & (tdmarket_data['ask'] != 0)][
            ['symbol', 'strikePrice', 'mark', 'daysToExpiration', 'bid', 'ask']]


        dfcalls = dfcalls.rename(
            columns={'symbol': 'callsymbol', 'mark': 'callmark', 'bid': 'callbid', 'ask': 'callask'})

        dfputts = tdmarket_data.loc[(tdmarket_data.putCall == 'PUT') & (tdmarket_data.mark != 0) & (tdmarket_data.bid != 0) & (tdmarket_data.ask != 0)][
            ['symbol', 'strikePrice', 'mark', 'daysToExpiration', 'bid', 'ask']]
        dfputts = dfputts.reindex()
        dfputts = dfputts.rename(columns={'symbol': 'putsymbol', 'mark': 'putmark', 'bid': 'putbid', 'ask': 'putask'})

        dfmerged = pd.merge(dfcalls, dfputts,how="inner", on=['strikePrice', 'daysToExpiration'])

        return dfmerged

    def getStrategyCalculate(self,row,shift):

        call_sum_price = row.callmark1-row.callmark2
        put_sum_price= +row.putmark2-row.putmark1
        dif_strike_price=row.strikePrice2-row.strikePrice1
        day_to_experation= row['daysToExpiration1']

        sum_of_strategy=call_sum_price + put_sum_price
        cost_of_margine = (1 * day_to_experation / 365 )*12/100

        # CASE 1: Non-tradable strategy (no volume)
        if sum_of_strategy == 0:
            # Return NaN for invalid metrics - will be filtered by handler
            return pd.Series([0, cost_of_margine, None, None, None])

        # CASE 2: Tradable strategy - apply CAP algorithm
        sum_of_strategy_capped = apply_spread_cap(sum_of_strategy, dif_strike_price, bound=0.01)

        # Calculate with capped values
        total_profit_loss = dif_strike_price - sum_of_strategy_capped - super().getFee() / 100 - cost_of_margine
        persantage_of_strategy = total_profit_loss / sum_of_strategy_capped
        year_interest_of_strategy = persantage_of_strategy * 365 / day_to_experation

        return pd.Series([sum_of_strategy_capped, cost_of_margine, total_profit_loss, persantage_of_strategy, year_interest_of_strategy])




    def getStrategyPreparedBasedata(self,tdmarket_data_json):
        # make dataframe from json
        tdmarket_data=self.getTDSingleOptionsDF(tdmarket_data_json)
        # merge calls and puts to strategu
        tdmarket_data_prepared=self.getStrategyFlatDataClened(tdmarket_data)


        # print(tdmarket_data)

        dfshifted = tdmarket_data_prepared.add_suffix('1').assign(**tdmarket_data_prepared.shift(-1).add_suffix('2'))
        dfcleaned=dfshifted.loc[(dfshifted.daysToExpiration1 == dfshifted.daysToExpiration2)]


        dfcleaned[['sum_of_strategy','cost_of_margine_of_strategy','total_profit_loss_of_strategy','persantage_of_strategy','year_interest_of_strategy']]\
            =dfcleaned.apply(lambda row : self.getStrategyCalculate(row,self.shifts),axis=1)


        return dfcleaned

    def getStrategyData(self):

        tdmarket_data_json = self.options(symbol=self.symbol,
                                    # strategy="ANALYTICAL",
                                    strategy="SINGLE",
                                    contractType='ALL',
                                    includeQuotes=True)

        dfmerged=self.getStrategyPreparedBasedata(tdmarket_data_json)

        return dfmerged





