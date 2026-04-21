# Legal and ethical guardrails

**This toolkit is for authorised security testing, research, and education only.**

## Authorisation requirement

Before using any hardware or software in this repository against a card, reader, or system you do not own personally, you must have **explicit written authorisation** from the system owner that covers:

- The specific systems, cards, and technologies in scope.
- The test window and physical locations.
- The techniques you intend to use (read, write, clone, relay, key recovery).
- The data you will collect, store, and destroy.

Without that authorisation, most uses of this toolkit against third-party systems are criminal offences in most jurisdictions.

## UK-specific notes

- **Computer Misuse Act 1990** — unauthorised access to computer material (s.1), unauthorised acts with intent to impair (s.3), and making/supplying articles for use in CMA offences (s.3A) all potentially apply to NFC cloning and relay attacks on live systems.
- **Fraud Act 2006** — cloning a payment instrument or using a relay against a payment terminal without authorisation is fraud by false representation (s.2) and/or possession of articles for use in fraud (s.6).
- **Forgery and Counterfeiting Act 1981** — cloning access credentials or identity documents.
- **Ofcom Interface Requirement 2030** — operation at 13.56 MHz at the PN532's power levels is licence-exempt under short-range device rules, so the radio emission itself is lawful. The misuse of what is emitted is what becomes unlawful.

## PCI DSS

Reading contactless EMV track-equivalent data, even from a card you own, may place you in scope of PCI DSS if the data is stored or transmitted. The CLI gates EMV features behind an explicit authorisation flag and refuses to persist PAN data unmasked.

## Do not commit

Do not commit any of the following to this repository:

- Real card dumps (MIFARE sector data, NTAG dumps, DESFire application data).
- Recovered keys for cards you do not own outright.
- Captured magstripe tracks from real cards.
- EMV data of any kind.
- Photographs or identifiers of readers, badges, or facilities you are testing.

`profiles/` and `*.mfd` are already in `.gitignore`. Keep them there.

## Responsible disclosure

If you discover a new vulnerability in a deployed access-control or payment system during authorised testing, follow the system owner's disclosure policy. Where none exists, a 90-day coordinated disclosure window aligned with industry norms is reasonable.

## Data handling

- Store captured profiles on encrypted media.
- Destroy captured data at the end of the engagement unless the scope explicitly requires retention.
- Scrub profiles of PAN, cardholder name, and any other sensitive fields before sharing, even internally.
