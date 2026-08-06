@transaction-capture @mvp
Feature: Capture a transaction from conversation
  The workflow progressively builds a transaction candidate, asks for required
  fields that remain missing, validates the completed candidate, creates the
  transaction, returns a compact summary, and closes the capture session.

  Background:
    Given the system date is "2026-08-04"
    And no capture session is active
    And the following accounts exist:
      | account_id     | display_name | currency | active | visible | accepts_transactions |
      | cash           | Cash         | USD      | true   | true    | true                 |
      | checking       | Checking     | USD      | true   | true    | true                 |
      | savings        | Savings      | USD      | true   | true    | true                 |
      | euro_savings   | Euro Savings | EUR      | true   | true    | true                 |
      | closed_account | Closed       | USD      | false  | true    | false                |
      | hidden_account | Hidden       | USD      | true   | false   | true                 |
    And the following categories exist:
      | category_id | display_name | category_type |
      | dining      | Dining       | spending      |
      | groceries   | Groceries    | spending      |
      | salary      | Salary       | income        |
      | bonus       | Bonus        | income        |

  Rule: Initialize and derive capture state

    Scenario: Default the transaction date to today
      When the user says "Record an expense"
      Then an active capture session exists
      And the candidate type is "expense"
      And candidate.occurred_on is "2026-08-04"
      And remaining_fields are exactly:
        | field                |
        | amount_minor         |
        | account_id           |
        | spending_category_id |
      And requested_field is "amount_minor"

    Scenario: Ask for the transaction type when it is missing
      When the user says "I need to record something"
      Then an active capture session exists
      And candidate.type is missing
      And remaining_fields are exactly:
        | field |
        | type  |
      And requested_field is "type"
      And the workflow asks for the transaction type

    Scenario Outline: Compute remaining fields in stable order
      Given an active candidate of type "<type>"
      And candidate.occurred_on is "2026-08-04"
      And no other required fields are populated
      When remaining_fields are recomputed
      Then remaining_fields are exactly "<remaining_fields>"
      And requested_field is "<requested_field>"

      Examples:
        | type       | remaining_fields                                                    | requested_field         |
        | expense    | amount_minor, account_id, spending_category_id                       | amount_minor            |
        | income     | amount_minor, account_id, income_category_id                         | amount_minor            |
        | transfer   | amount_minor, source_account_id, destination_account_id              | amount_minor            |
        | adjustment | account_id, balance_change_minor                                     | account_id              |

  Rule: Capture complete transactions in one message

    Scenario: Capture a complete expense
      When the user says "Spent $40 from Cash on Dining yesterday"
      Then the candidate is:
        | field                | value      |
        | type                 | expense    |
        | amount_minor         | 4000       |
        | account_id           | cash       |
        | spending_category_id | dining     |
        | occurred_on          | 2026-08-03 |
      And remaining_fields are empty
      And the candidate is validated
      And one transaction is created

    Scenario: Capture complete income
      When the user says "Received $2,500 salary into Checking today"
      Then the candidate is:
        | field              | value      |
        | type               | income     |
        | amount_minor       | 250000     |
        | account_id         | checking   |
        | income_category_id | salary     |
        | occurred_on        | 2026-08-04 |
      And remaining_fields are empty
      And the candidate is validated
      And one transaction is created

    Scenario: Capture a complete transfer
      When the user says "Transfer $500 from Checking to Savings"
      Then the candidate is:
        | field                  | value      |
        | type                   | transfer   |
        | amount_minor           | 50000      |
        | source_account_id      | checking   |
        | destination_account_id | savings    |
        | occurred_on            | 2026-08-04 |
      And remaining_fields are empty
      And the candidate is validated
      And one transaction is created

    Scenario Outline: Capture a signed balance adjustment
      When the user says "<message>"
      Then the candidate is:
        | field                | value                  |
        | type                 | adjustment             |
        | account_id           | cash                   |
        | balance_change_minor | <balance_change_minor> |
        | occurred_on          | 2026-08-04             |
      And remaining_fields are empty
      And the candidate is validated
      And one transaction is created

      Examples:
        | message             | balance_change_minor |
        | Increase Cash by $50 | 5000                 |
        | Reduce Cash by $20   | -2000                |

  Rule: Progressively fill and replace candidate fields

    Scenario: Ask for one missing expense field
      When the user says "Spent $40 on Dining"
      Then candidate.type is "expense"
      And candidate.amount_minor is 4000
      And candidate.spending_category_id is "dining"
      And candidate.occurred_on is "2026-08-04"
      And candidate.account_id is missing
      And remaining_fields are exactly:
        | field      |
        | account_id |
      And requested_field is "account_id"
      And the workflow asks "Which account did you use?"
      When the user says "Cash"
      Then candidate.account_id is "cash"
      And remaining_fields are empty
      And one transaction is created

    Scenario: Collect a transfer over two turns
      When the user says "Transfer $100 from Checking"
      Then candidate.type is "transfer"
      And candidate.amount_minor is 10000
      And candidate.source_account_id is "checking"
      And candidate.destination_account_id is missing
      And candidate.occurred_on is "2026-08-04"
      And requested_field is "destination_account_id"
      And the workflow asks "Which account did you transfer it to?"
      When the user says "Savings"
      Then candidate.destination_account_id is "savings"
      And remaining_fields are empty
      And one transaction is created

    Scenario: Interpret a short answer as the requested amount
      Given an active expense candidate
      And candidate.occurred_on is "2026-08-04"
      And requested_field is "amount_minor"
      When the user says "35"
      Then candidate.amount_minor is 3500
      And the value is not applied to another candidate field

    Scenario: Apply all recognized fields from a follow-up answer
      Given an active expense candidate
      And candidate.occurred_on is "2026-08-04"
      And requested_field is "amount_minor"
      When the user says "$35 from Cash for Groceries"
      Then candidate.amount_minor is 3500
      And candidate.account_id is "cash"
      And candidate.spending_category_id is "groceries"
      And remaining_fields are empty
      And one transaction is created

    Scenario: Replace a previously captured field
      Given an active expense candidate with:
        | field                | value      |
        | amount_minor         | 2500       |
        | account_id           | cash       |
        | spending_category_id | dining     |
        | occurred_on          | 2026-08-04 |
      When the user says "Actually, I used Checking"
      Then candidate.account_id is "checking"
      And candidate contains no previous value or correction metadata for account_id
      And remaining_fields are empty
      And one transaction is created

    Scenario: Replace the default date with a user-provided date
      Given an active expense candidate
      And candidate.occurred_on is "2026-08-04"
      When the user says "This happened yesterday"
      Then candidate.occurred_on is "2026-08-03"

    Scenario: Preserve optional metadata without blocking completion
      When the user says "Spent $25 from Cash on Dining at Corner Cafe. Team lunch."
      Then candidate.type is "expense"
      And candidate.amount_minor is 2500
      And candidate.account_id is "cash"
      And candidate.spending_category_id is "dining"
      And candidate.merchant_name is "Corner Cafe"
      And candidate.description is "Team lunch"
      And remaining_fields are empty
      And one transaction is created

  Rule: Validate complete candidates and recover invalid fields

    Scenario Outline: Reject a zero monetary value
      Given a complete "<type>" candidate
      And candidate.<field> is 0
      When the candidate is validated
      Then validation fails for "<field>"
      And candidate.<field> is cleared
      And remaining_fields include "<field>"
      And requested_field is "<field>"
      And no transaction is created

      Examples:
        | type       | field                |
        | expense    | amount_minor         |
        | income     | amount_minor         |
        | transfer   | amount_minor         |
        | adjustment | balance_change_minor |

    Scenario Outline: Reject an unusable account
      Given a complete expense candidate using account "<account_id>"
      When the candidate is validated
      Then validation fails for "account_id"
      And candidate.account_id is cleared
      And remaining_fields are exactly:
        | field      |
        | account_id |
      And requested_field is "account_id"
      And no transaction is created

      Examples:
        | account_id     |
        | closed_account |
        | hidden_account |
        | missing_account |

    Scenario: Reject a non-spending category for an expense
      Given a complete expense candidate using spending_category_id "salary"
      When the candidate is validated
      Then validation fails for "spending_category_id"
      And candidate.spending_category_id is cleared
      And requested_field is "spending_category_id"
      And no transaction is created

    Scenario: Reject a non-income category for income
      Given a complete income candidate using income_category_id "dining"
      When the candidate is validated
      Then validation fails for "income_category_id"
      And candidate.income_category_id is cleared
      And requested_field is "income_category_id"
      And no transaction is created

    Scenario: Reject a transfer whose source and destination are the same
      Given a complete transfer candidate with:
        | field                  | value      |
        | amount_minor           | 10000      |
        | source_account_id      | checking   |
        | destination_account_id | checking   |
        | occurred_on            | 2026-08-04 |
      When the candidate is validated
      Then validation fails because the transfer accounts are the same
      And at least one of source_account_id or destination_account_id is cleared
      And remaining_fields include the cleared account field
      And requested_field is the cleared account field
      And no transaction is created

    Scenario: Reject a transfer whose accounts use different currencies
      Given a complete transfer candidate with:
        | field                  | value        |
        | amount_minor           | 10000        |
        | source_account_id      | checking     |
        | destination_account_id | euro_savings |
        | occurred_on            | 2026-08-04   |
      When the candidate is validated
      Then validation fails because the account currencies differ
      And at least one of source_account_id or destination_account_id is cleared
      And remaining_fields include the cleared account field
      And requested_field is the cleared account field
      And no transaction is created

    Scenario: Reject a date that the transaction service does not accept
      Given the transaction service rejects the date "1900-01-01"
      And a complete expense candidate occurred on "1900-01-01"
      When the candidate is validated
      Then validation fails for "occurred_on"
      And candidate.occurred_on is cleared
      And remaining_fields are exactly:
        | field       |
        | occurred_on |
      And requested_field is "occurred_on"
      And no transaction is created

    Scenario: Record after replacing an invalid field
      Given a complete expense candidate using account "closed_account"
      When the candidate is validated
      Then candidate.account_id is cleared
      And requested_field is "account_id"
      When the user says "Cash"
      Then candidate.account_id is "cash"
      And remaining_fields are empty
      And the candidate is validated again
      And one transaction is created

  Rule: Construct postings only after capture is complete and valid

    Scenario: Do not create a transaction while required fields remain
      When the user says "Record an expense"
      Then remaining_fields are not empty
      And the transaction service has not been called
      And no postings have been constructed

    Scenario: Construct expense postings from the completed candidate
      When the user says "Spent $40 from Cash on Dining"
      Then the transaction contains these postings:
        | posting_target | target_id | amount_minor | currency |
        | account        | cash      | -4000        | USD      |
        | category       | dining    | 4000         | USD      |

    Scenario: Construct income postings from the completed candidate
      When the user says "Received $2,500 Salary into Checking"
      Then the transaction contains these postings:
        | posting_target | target_id | amount_minor | currency |
        | account        | checking  | 250000       | USD      |
        | category       | salary    | -250000      | USD      |

    Scenario: Construct transfer postings from the completed candidate
      When the user says "Transfer $500 from Checking to Savings"
      Then the transaction contains these postings:
        | posting_target | target_id | amount_minor | currency |
        | account        | checking  | -50000       | USD      |
        | account        | savings   | 50000        | USD      |

    Scenario: Construct an adjustment account posting
      When the user says "Increase Cash by $50"
      Then the transaction contains an account posting:
        | target_id | amount_minor | currency |
        | cash      | 5000         | USD      |
      And the transaction service creates the balancing system-equity posting

  Rule: Finish after successful transaction creation

    Scenario: Return a compact summary and close the capture session
      When the user says "Spent $40 from Cash on Dining"
      And the transaction service returns the created transaction
      Then the workflow responds with a compact summary equivalent to:
        "Recorded: $40 Dining expense from Cash for today."
      And the capture session is closed
      And no candidate is active
      And requested_field is cleared

# Deferred from the executable MVP suite because the source does not define
# an interaction policy or explicitly places the behavior outside scope:
#
# - Cancel an active capture.
# - Start another transaction while a capture session is active.
# - Resolve ambiguous account or category names.
# - Handle an unrelated answer while requested_field is set.
# - Handle transaction-service creation failures after validation.
# - Confirm before recording.
# - Edit, void, or refund an existing transaction.
# - Capture split expenses.
# - Capture multi-currency transfers.
# - Capture a target balance such as "set Cash to $500".
