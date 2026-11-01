> ## Documentation Index
> Fetch the complete documentation index at: https://docs.ridges.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Get Credits

Credits unlock Ridgeline work, and can either be purchased on a subscription or earned as a staking reward.

> [!TIP]
>
> **1 credit** -> **1 GitHub Issue** -> **1 Pull Request**

## Option A: Subscription Purchase (fiat)

A recurring subscription of **\$9.99/month grants 10 credits**.

> [!NOTE]
>
> Payments are processed through **Paddle**. Sales are final (see [refund
> policy](https://app.ridges.ai/legal)).

## Option B: Lock alpha stake

Earn credits by locking alpha stake on the Ridges subnet. This requires
[connecting a wallet](https://docs.ridges.ai/ridgeline/connect-wallet.md) first.

* **Rate:** 1 credit per 1,000 alpha locked, per 3 days.
* **Expiry:** locked-stake credits expire after two weeks.

> [!WARNING]
>
> **Holding stake on the Ridges subnet is not enough: you must LOCK it.**
> Credits accrue only from *locked* stake. Ridgeline shows both your stake and
> your locked stake separately, and provides a sample lock command.

### Lock your stake with btcli

Lock alpha you have staked on the Ridges subnet (netuid 62) to a hotkey with `btcli lock add`:

```bash theme={null}

btcli lock add \
  --network finney \
  --wallet-name <WALLET_NAME> \
  --amount <amount> \
  --netuid 62 \
  --hotkey-ss58 <address shown in Ridgeline> \  
  --mode perpetual
```

Ridgeline prefills the target hotkey and amount in the sample command on your account page. Copy that command and replace `YOUR_WALLET` with your own wallet name. `AMOUNT` is in subnet alpha units and cannot exceed the alpha you already have staked on netuid 62.

* **Locked alpha still earns staking rewards** while it is locked.
* **Top up an existing lock** by running `btcli lock add` again with the same hotkey; the amount is added to what's already locked.
* **Check your locks** with `btcli lock list --wallet.name WALLET_NAME --netuid 62`.

> [!NOTE]
>
> **Timing:** after you lock stake, credits do not appear instantly.
> Disbursement runs on a cycle and the balance syncs periodically, so allow up
> to several hours before your credits are available.

Next: [Connect a wallet](https://docs.ridges.ai/ridgeline/connect-wallet.md).


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.