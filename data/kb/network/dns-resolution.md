# Internal sites not found (DNS resolution failure)

## Symptoms
- Browser shows "server not found" or "this site can't be reached" for internal sites
- Hostnames fail but IP addresses work

## Checks
- Resolve an internal hostname (intranet.corp.local)
- Check which DNS server responded

## Resolution
A stale DNS cache or resolver entry is the usual cause. Ask the user to run
`ipconfig /flushdns` in Command Prompt, reconnect to the network, and retry.
If lookups still fail, escalate to Network L2 to check the resolver.
