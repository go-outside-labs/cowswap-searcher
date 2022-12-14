# -*- encoding: utf-8 -*-
# apis/uniswapv2.py
# This class implements an api for trading tokens on AMMs reserves
# governed by constant product, such as Uniswap V2 (and its forks).

from decimal import Decimal
from src.util.arithmetics import div, to_decimal


class ConstantProductAmmApi():

    def __init__(self, order, amms):

        # Order data
        self.__buy_amount = to_decimal(order['buy_amount'])
        self.__sell_amount = to_decimal(order['sell_amount'])
        self.__is_sell_order = bool(order['is_sell_order'])
        self.__allow_partial_fill = bool(order['allow_partial_fill'])

        # Reserves data
        self.__buy_token_reserve = to_decimal(amms['buy_reserve'])
        self.__sell_token_reserve = to_decimal(amms['sell_reserve'])

    ###############################
    #     Private methods         #
    ###############################

    def _get_exec_sell_amount(self) -> Decimal:
        """
            Implement the constant-product relation for the retrieval of 
            tokens B from selling an amount t of tokens A in an AB pool, 
            where a and b are the initial token reserves:
                 δ    ≤    (b − a * b) / (a + t)    =    (b * t) / (a + t)
        """

        return div((self.__buy_token_reserve * self.__sell_amount),
                   (self.__sell_token_reserve + self.__sell_amount))

    def _get_exec_buy_amount(self) -> Decimal:
        raise NotImplementedError

    def _can_fill_order(self, exec_amount, limit_amount) -> bool:
        """Verify whether the order checks the limit price constraint."""

        if self.__allow_partial_fill:
            return exec_amount <= limit_amount
        return exec_amount == limit_amount


    ###############################
    #     Public methods          #
    ###############################

    @staticmethod
    def get_token_price(token_balance, pair_token_balance) -> float:
        """Return the current (market) price for a token in the pool."""

        return float(div(pair_token_balance, token_balance))

    @staticmethod
    def get_exchange_rate(sell_reserve, buy_reserve) -> float:
        """Calculate the exchange rate between a pair of tokens."""

        return float(div(buy_reserve, sell_reserve))

    @staticmethod
    def calculate_surplus(exec_amount, amount) -> Decimal:
        """
            Calculate the surplus of an executed order.
        """

        return int(exec_amount - amount)

    def trade_sell_order(self) -> dict:
        """
            Get sell limit order data for a list of reserves.

            In this type of trade, the order would add "sell_token" to the reserve at the
            value of "sell_amount" and retrieve "buy_token" at a calculated "exec_buy_amount".
            This would have the inverse trade in the amm: the reserve would receive token A
            at the amount "amm_exec_buy_amount" (which matches the order's exec_sell_amount),
            and would lose token C at "amm_exec_sell_amount" (orders' exec_buy_amount).
        """

        # Calculate order execution data
        amm_exec_buy_amount = int(self.__sell_amount)
        amm_exec_sell_amount = int(self._get_exec_sell_amount())

        # Calculate surplus for this sell order
        surplus = self.calculate_surplus(amm_exec_sell_amount, self.__buy_amount)

        # Check limit price for amm_exec_sell_ammount
        can_fill = self._can_fill_order(amm_exec_buy_amount, self.__sell_amount)

        # Get some extra data on the reserve
        prior_sell_token_reserve = int(self.__sell_token_reserve)
        prior_buy_token_reserve = int(self.__buy_token_reserve)
        updated_sell_token_reserve = int(self.__sell_token_reserve + amm_exec_buy_amount)
        updated_buy_token_reserve = int(self.__buy_token_reserve - amm_exec_sell_amount)

        # Get some extra data on the prices
        prior_buy_price = float(self.get_exchange_rate(
                                    prior_sell_token_reserve, prior_buy_token_reserve))
        market_buy_price = float(self.get_token_price(
                                    updated_sell_token_reserve, updated_buy_token_reserve))
        prior_sell_price = float(self.get_exchange_rate(
                                    prior_buy_token_reserve, prior_sell_token_reserve))
        market_sell_price = float(self.get_token_price(
                                    updated_buy_token_reserve, updated_sell_token_reserve))

        return {
                'trade_surplus': surplus,
                'prior_buy_price': prior_buy_price,
                'market_buy_price': market_buy_price,
                'prior_sell_price': prior_sell_price,
                'market_sell_price': market_sell_price,
                'updated_sell_token_reserve': updated_sell_token_reserve,
                'updated_buy_token_reserve': updated_buy_token_reserve,
                'prior_sell_token_reserve': prior_sell_token_reserve,
                'prior_buy_token_reserve': prior_buy_token_reserve,
                'amm_exec_sell_amount': amm_exec_buy_amount,
                'amm_exec_buy_amount': amm_exec_sell_amount,
                'can_fill': can_fill
        }

    def trade_buy_order(self) -> dict:
        """Get buy limit order data for a list of reserves."""
        raise NotImplementedError

    def solve(self) -> dict:
        """Entry point for this class."""

        if self.__is_sell_order:
            return self.trade_sell_order()
        return self.trade_buy_order()
