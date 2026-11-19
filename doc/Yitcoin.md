# Yitcoin GBT support

This fork understands the Yitcoin `yitcoin-owner-reward` extension to
`getblocktemplate`. When the Yitcoin node activates its 2% owner subsidy, the
miner reserves the returned owner amount and script in the coinbase
transaction, then pays the remaining subsidy and transaction fees to the
configured `--coinbase-addr`.

Use this miner only with a Yitcoin node that implements the same extension.
An unmodified miner will not advertise support and the activated node will
refuse its mining-template request. This source change does not change the
network rules by itself; the matching Yitcoin Core consensus change is
required.
