# VPN connection fails or drops after sign-in

## Symptoms
- VPN client shows "Disconnected" or keeps reconnecting
- Internal sites (intranet, file shares) unreachable while working remotely
- Error mentions authentication, token or session expired

## Checks
- Check VPN client status and last error for the user
- Ping the VPN gateway and resolve an internal hostname

## Resolution
Ask the user to sign out of the VPN client, sign back in, and approve the MFA prompt.
Expired auth tokens are the most common cause and are fixed by a fresh sign-in.
If the client still fails after re-authentication, escalate to Network L2 with the client error.
