def main():
    """Legacy live diagnostic intentionally disabled in free-tier mode.

    Provider/model compatibility is covered by mocked tests. Ad-hoc model-list
    calls bypassed the project budget ledger and could consume quota merely by
    running this helper, so this file is now a safe explanatory entry point.
    """
    print(
        "Live Gemini model-list diagnostikasi o'chirilgan: u global supply "
        "ledgerini chetlab o'tardi. Offline tekshiruv uchun "
        "`python manage.py test ai.providers.tests` ni ishlating."
    )


if __name__ == "__main__":
    main()
