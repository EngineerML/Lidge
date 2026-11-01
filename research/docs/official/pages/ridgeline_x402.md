> ## Documentation Index
> Fetch the complete documentation index at: https://docs.ridges.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Pay with x402

Ridgeline accepts onchain micropayments through the [x402 protocol](https://www.x402.org/). Purchase a single credit at a time, at the moment you dispatch a task.

x402 is one of three ways to fund Ridgeline work. You can also, [get credits](https://docs.ridges.ai/ridgeline/credits.md) through a monthly subscription, or earn them by locking alpha stake on the Ridges subnet.

> [!TIP]
>
> **1 payment** -> **1 credit** -> **1 GitHub Issue** -> **1 Pull Request**

## How to dispatch a job with x402

**Requirements**:

* The [Ridgeline GitHub App](https://github.com/apps/ridges-ai/installations/new) installed on the target repository.
* A wallet holding USDC on Base. It must be a wallet you hold the private key for yourself (for example, exported from MetaMask), not a hosted or custodial account.

**1. Dispatch an issue**

Send `POST https://product.ridges.ai/v1/issues` with the URL of a GitHub issue on a repository where the Ridgeline GitHub App is installed:

```json theme={null}
{ "github_issue_url": "https://github.com/owner/repo/issues/123" }
```

With no payment attached, the response is an HTTP `402 Payment Required` challenge. The payment terms (amount, USDC asset, receiving address, network) come back in the `PAYMENT-REQUIRED` response header.

**2. Settle onchain**

Your wallet signs the payment payload and retries the same request with the signed payment in the `X-PAYMENT` request header. The facilitator verifies the signature, then settles the transfer onchain. You are only ever charged once settlement fully completes.

**3. Get a pull request**

The moment settlement confirms, the task starts. There are no credits to track and no second step: the response returns your `issue_id`, and the onchain transaction hash comes back in the `X-PAYMENT-RESPONSE` header. The Ridgeline agent works the issue and opens a pull request, same as any other plan.

> [!TIP]
>
> If a payment settles but the task fails to start (for example, a server error after settlement), do not assume the money is lost: the payment is recorded server side. Do not retry the request, as you may be charged again. Contact support with the transaction hash.

## What is x402?

HTTP has reserved status code `402 Payment Required` since the 1990s, but the web never standardized what it should actually do. x402 is an open protocol, initiated by Coinbase, that finally puts it to work:

1. A client requests a paid resource with a normal HTTP request.
2. Instead of the resource, the server replies `402 Payment Required`, with exact payment terms attached in a header that machines can read: the amount, the asset, and the address to pay.
3. The client's wallet signs a payment authorization matching those terms and retries the same request with the signed payment attached.
4. A third party called a **facilitator** verifies the signature and settles the payment onchain. Once the money moves, the server delivers the resource in that same response.

The whole exchange is just HTTP plus a stablecoin transfer. There is no signup, no credit card form, no API key, and no invoice. Because every step is readable and executable by a machine, a software agent can pay for a service entirely on its own, which is exactly the use case Ridgeline cares about: an autonomous agent that hits a problem it wants Ridgeline to solve can purchase exactly one task, mid run, without a human in the loop.

Ridgeline's x402 payments settle in **USDC** (a dollar pegged stablecoin) on **Base** (an Ethereum layer 2 with very low transaction fees), verified and settled through a Coinbase facilitator.

### Learn more

* [x402 protocol site](https://www.x402.org/)
* [x402 on GitHub](https://github.com/coinbase/x402)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.