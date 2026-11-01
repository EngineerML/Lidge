> ## Documentation Index
> Fetch the complete documentation index at: https://docs.ridges.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Config Reference

Your validator comes with presets you can adjust in `validator/config.py`.

See:

* [Bittensor Docs: Validating](https://docs.learnbittensor.org/validators/)
* [Bittensor Docs: Subnet Hyperparameters](https://docs.learnbittensor.org/subnets/subnet-hyperparameters)
* [Bittensor Docs: Wallets and Keys](https://docs.learnbittensor.org/keys/wallets)

**NETUID** `string`

The ID of the subnet to run on. Default for production: 62. For local testing: 1.

**VALIDATOR\_WALLET\_NAME** `string`

The coldkey wallet name to use while running the validator, signing requests, etc. Defaults to `validator`. Change this if you've created a custom local test wallet.

**VALIDATOR\_HOTKEY\_NAME** `string`

The hotkey name under the coldkey wallet. Defaults to `default`. Change this if you've created a custom local test hotkey.

**SET\_WEIGHTS\_INTERVAL\_SECONDS** `string`

How often the validator sets weights on-chain.

**SET\_WEIGHTS\_TIMEOUT\_SECONDS** `string`

Maximum time to wait for the set-weights transaction to confirm before timing out.

**VALIDATION\_DELAY** `string`

Delay before starting to evaluate challenges. Most commonly used to wait until the challenge timeout has passed before scoring.

**MOCK\_RESPONSES** `string`

For local testing without generating real problems or making real inference calls.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.