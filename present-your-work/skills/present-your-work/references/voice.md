# The voice, by example

Three short reports, each written twice: first the way a model writes by default, then the way a
colleague would say it. The tasks are invented. Read the pairs for the difference in voice; the
second of each is the target.

## A bug fix

What a model writes by default:

> **Summary:** Fixed the timezone bug in the date parser. The root cause: `parse_date` was
> interpreting naive timestamps as UTC rather than local time — leading to off-by-one-day errors
> for users east of Greenwich. I've updated the parsing logic, added comprehensive tests, and
> verified that everything works as expected. **Next steps:** Consider auditing other call sites
> for similar issues. Let me know if you'd like me to make any further changes!

The same report, said:

> The dates are right now for people east of Greenwich. `parse_date` read timestamps without a
> zone as UTC, so anyone ahead of UTC saw yesterday's date after midnight. It now treats them as
> local time, which is what the export writes. Two other functions read timestamps the same way. I haven't
> touched them, because one of them feeds the billing report and I didn't want to change billing
> without asking you. Should I fix those too?

## A speed-up

What a model writes by default:

> I've significantly improved the performance of the search endpoint. Key changes:
>
> - **Caching:** Added a robust caching layer to reduce redundant database queries.
> - **Indexing:** Created a new index on `products.name`, ensuring faster lookups.
> - **Pagination:** Optimized pagination for better scalability.
>
> These changes result in a dramatic reduction in latency, making the search experience seamless
> for users.

The same report, said:

> Search now answers in about 80 ms instead of 900. Nearly all of it came from one index on
> `products.name`. Before that, the database read the whole table for every query. I also tried caching
> results, but it saved only another 10 ms and would have shown stale prices, so I took it out.
> Those times are from a copy of last week's data, so production may differ a little. If
> you're happy with it, the index takes about two minutes to build, so it's best added outside
> shop hours.

## Work that isn't finished

What a model writes by default:

> I've made substantial progress on the migration to the new payment provider. The integration is
> now largely complete, with the core payment flow fully implemented. However, there are a few
> remaining items to address: refunds are not yet supported, and webhook handling requires further
> testing. Overall, the migration is on track and should be ready soon.

The same report, said:

> Card payments go through the new provider now, but refunds don't, so we can't switch over yet.
> Their refund call needs the original charge ID, and we only kept our own order number. I've
> started storing their ID on new orders. For older orders we'll have to look it up through their
> API, and I don't know yet whether that works for charges more than a year old. I've asked their
> support. Until they answer, the old provider has to stay on for refunds.

## What changed between each pair

- The answer comes first, as a plain statement, and the catch is in the same breath.
- There are no labels, no bold, no bullets for things that connect, and no closing offer.
- There's no proof in them. No test counts, no commands, no "verified that". The reader can ask.
- The why is concrete. It names the cause and the alternative that was dropped, and why it was dropped.
- Sentences vary in length, use contractions, and sound like one person talking to another.
