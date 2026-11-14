# Loan Reset Alert: project notes

## The idea
A tool for Indian borrowers with floating-rate loans. It:
- tracks RBI repo decisions and banks' MCLR and repo-linked (EBLR/RLLR) rates
- works out a loan's next reset date and the EMI change
- writes a repricing request letter to the bank

Money: freemium (free alerts; about Rs 99-199/month for refinance comparisons and letters), or white-label to apps like BankBazaar or Paisabazaar.
Ankush is a beginner: explain things simply.

## Built so far
- Page "Loan Reset Alert": calculator, repricing letter, rates table for 12 banks.
  - website project_id 313fa3ac-a8d6-47c9-b065-c6bd23f34734
  - shared link: https://hark.com/site/313fa3ac-a8d6-47c9-b065-c6bd23f34734
- Daily 8:00 IST scheduled task (08da1a0e, lives in the main chat) rechecks official bank rates and updates the Page.

## Rates as checked 12 Nov 2026
- RBI repo 5.50% (raised 25 bps on 7 Oct 2026)
- SBI: 1-yr MCLR 8.85%, 2-yr 8.90%; EBLR 8.15% + CRP + BSP; RLLR 7.75% + CRP (from 15 Oct 2026)
- PNB 1-yr MCLR 8.90% (from 1 Nov)
- Bank of Baroda 8.85% (from 12 Nov)
- Bank of India 8.90% (from 1 Nov)
- Indian Bank 8.95% (from 3 Nov); RBLR 8.20%
- HDFC MCLR 7.85-8.70% (from 7 Nov)
- Canara +10 bps (from 12 Nov)
- ICICI 9.15% and Kotak 8.30%: indicative, third-party tracker
- Union Bank EBLR 8.25% (from 8 Oct)
(Latest values live on the Page; the daily task keeps them current.)

## Next steps (proposed, awaiting Ankush's pick)
1. Validate demand: talk to 20 floating-rate borrowers (do they know their reset date? would they pay?).
2. Build a WhatsApp/Telegram alert bot that pings on repo/MCLR changes.
