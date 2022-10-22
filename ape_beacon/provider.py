from abc import ABC
from typing import Optional

from ape.api.networks import LOCAL_NETWORK_NAME
from ape.api.providers import BlockAPI, ProviderAPI
from ape.api.transactions import TransactionAPI
from ape.exceptions import APINotImplementedError, BlockNotFoundError, ProviderNotConnectedError
from ape.types import BlockID
from ape.utils import cached_property
from web3.beacon import Beacon

from ape_beacon.exceptions import ValidatorNotFoundError


class BeaconProvider(ProviderAPI, ABC):
    """
    A base provider mixin class that uses the
    `web3.py Beacon API
    <https://web3py.readthedocs.io/en/latest/web3.beacon.html>`__ python package.
    """

    # NOTE: Read only provider given web3.py Beacon API implementation

    _beacon: Optional[Beacon]
    _client_version: Optional[str] = None

    @property
    def beacon(self) -> Beacon:
        """
        Access to the ``beacon`` object as if you did ``Beacon(uri)``.
        """
        if not self._beacon:
            raise ProviderNotConnectedError()

        return self._beacon

    @cached_property
    def client_version(self) -> str:
        """
        As if you did ``Beacon(uri).get_version()``.
        """
        if not self._beacon:
            return ""

        # NOTE: Gets reset to `None` on `connect()` and `disconnect()`.
        if self._client_version is None:
            resp = self.beacon.get_version()
            if "data" not in resp or "version" not in resp["data"]:
                return ""

            self._client_version = resp["data"]["version"]

        return self._client_version

    @property
    def base_fee(self) -> int:
        raise APINotImplementedError("base_fee is not implemented by this provider.")

    @property
    def max_gas(self) -> int:
        raise APINotImplementedError("max_gas is not implemented by this provider.")

    @property
    def supports_tracing(self) -> bool:
        raise APINotImplementedError("supports_tracing is not implemented by this provider.")

    def estimate_gas_cost(self, txn: TransactionAPI, **kwargs) -> int:
        raise APINotImplementedError("estimate_gas_cost is not implemented by this provider.")

    @property
    def gas_price(self) -> int:
        raise APINotImplementedError("gas_price is not implemented by this provider.")

    @property
    def priority_fee(self) -> int:
        raise APINotImplementedError("priority_fee is not implemented by this provider.")

    def get_nonce(self, address: str, **kwargs) -> int:
        raise APINotImplementedError("get_nonce is not implemented by this provider.")

    def update_settings(self, new_settings: dict):
        self.disconnect()
        self.provider_settings.update(new_settings)
        self.connect()

    @property
    def is_connected(self) -> bool:
        if self._beacon is None:
            return False

        status_code = self._beacon.get_health()
        return status_code == 200

    @cached_property
    def chain_id(self) -> int:
        default_chain_id = None
        if self.network.name not in (
            "adhoc",
            LOCAL_NETWORK_NAME,
        ) and not self.network.name.endswith("-fork"):
            # If using a live network, the chain ID is hardcoded.
            default_chain_id = self.network.chain_id

        try:
            # use deposit contract endpoint for chain ID
            resp = self.beacon.get_deposit_contract()
            if "data" in resp and "chain_id" in resp["data"]:
                return resp["data"]["chain_id"]

        except ProviderNotConnectedError:
            if default_chain_id is not None:
                return default_chain_id

            raise  # Original error

        if default_chain_id is not None:
            return default_chain_id

        raise ProviderNotConnectedError()

    def get_block(self, block_id: BlockID) -> BlockAPI:
        """
        As if you did ``Beacon(uri).get_block(block_id)``.
        """
        # TODO: handle raise_for_status errors from Beacon

        if isinstance(block_id, str) and block_id.isnumeric():
            block_id = int(block_id)

        resp = self.beacon.get_block(str(block_id))
        if "data" not in resp or "message" not in resp["data"]:
            raise BlockNotFoundError(block_id)

        block_data = resp["data"]["message"]
        return self.network.ecosystem.decode_block(block_data)

    def get_balance(self, address: str) -> int:
        """
        Gets the validator balance for validator address or ID on beacon chain.
        """

        # TODO: handle raise_for_status errors from Beacon

        resp = self.beacon.get_validator(validator_id=address)
        if "data" not in resp or "balance" not in resp["data"]:
            raise ValidatorNotFoundError(address)

        balance = resp["data"]["balance"]
        return balance
