# Commune Payment Mechanism Brainstorm

## Constraints
- minimum floor: 1 PLN / user / month
- must cover: monthly LLM usage (tokens consumed by the commune)
- must encourage: sharing/inviting friends

## How it could work

### Option A: Simple split
Total commune cost = base platform fee + total LLM usage of all members last month.
Price per user = total commune cost / number of members.

- **Pro**: dead simple, transparent math
- **Con**: heavy users subsidized by light users, could cause resentment
- **Floor**: never goes below 1 PLN/user/month

### Option B: Base + usage weighted split
Each user pays: 1 PLN base + (their_tokens / total_commune_tokens) * total_LLM_cost.

- **Pro**: fairer, heavy users pay more
- **Con**: less incentive to invite friends (your cost is mostly your own usage)
- **Compromise**: could weight it 50/50 between equal split and usage-proportional

### Option C: Tiered decay (recommended to explore)
Starting price: e.g. 30 PLN/month for the first user.
Each new member reduces everyone's price by a decay factor.

```
price = max(1 PLN, starting_price * decay_factor ^ (num_members - 1))
```

Example with starting_price=30 PLN, decay_factor=0.85:
- 1 member:  30.00 PLN
- 5 members: 15.69 PLN
- 10 members: 6.85 PLN
- 20 members: 1.72 PLN
- 25 members: 1.00 PLN (floor)

- **Pro**: strong viral incentive, price drops are visible and exciting
- **Con**: need to calibrate decay_factor so we don't go bankrupt. LLM costs scale with users while revenue asymptotes
- **Safety valve**: the cat gets "tired" when commune usage exceeds a hidden budget, naturally throttling costs

### Option D: Commune has a shared wallet
The commune has a monthly token budget = sum of all member contributions - platform fee.
When the budget runs out the cat is tired for everyone until next month.

- **Pro**: self-regulating, commune members police each other naturally
- **Con**: one heavy user could drain the whole commune

## Open questions
- Should commune members see each other's usage? (leaderboard could serve this purpose)
- Can a user be in multiple communes?
- What happens when someone leaves — does everyone else's price go up?
- Should there be a max commune size?
- How do we handle the transition month when new members join mid-billing?
- Do we want a free trial period before forcing payment?

## Viral mechanics to consider
- Invite link gives both inviter and invitee a bonus (extra tokens for a week?)
- "Your commune saved X PLN this month because Y joined" notifications
- Commune naming / identity to build belonging
- Leaderboard: "fattest cat" = most active user, creates friendly competition

## Revenue safety
Whatever model we pick, we need a hard cost ceiling per commune:
`max_monthly_cost_per_commune = num_members * price_per_member * some_margin`

If LLM costs exceed this, the cat sleeps. This is the fundamental safety mechanism.
