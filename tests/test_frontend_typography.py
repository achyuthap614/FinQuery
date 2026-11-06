"""Tests for frontend Markdown typography, heading hierarchy, and list formatting."""
import re
import markdown_it
from frontend.app import format_chat_markdown

md = markdown_it.MarkdownIt()

def test_long_multisection_markdown_response():
    """Verifies that a long multi-section RAG response is not wrapped in a single heading."""
    raw_rag_response = (
        "### 📚 Financial Knowledge Explanation\n\n"
        "# Compound Interest and the Time Value of Money "
        "Compound interest is the interest calculated on the initial principal and also on the "
        "accumulated interest of previous periods of a deposit or loan. Often referred to as 'interest on interest,' "
        "it causes wealth to grow at an exponential rate rather than a linear rate. "
        "## The Mathematical Formula The future value of an investment with compound interest is calculated using: "
        "A = P * (1 + r/n)^(n*t) Where: - A = the future value of the investment or loan, including interest "
        "- P = the principal investment amount (the initial deposit or loan balance) "
        "- r = the annual nominal interest rate (in decimal form, e.g., 7% = 0.07) "
        "## The Rule of 72 The Rule of 72 is a quick, handy mental shortcut to estimate the number of years required to double: "
        "- At a 6% return: 72 / 6 = 12 years to double. "
        "- At an 8% return: 72 / 8 = 9 years to double.\n\n"
        "---\n"
        "**References & Sources:**\n"
        "- 📄 **compound_interest.txt** (Chunk 0, Similarity: 0.52)"
    )

    formatted = format_chat_markdown(raw_rag_response)
    rendered_html = md.render(formatted)

    # 1. Ensure the entire response is NOT inside a heading element
    assert not rendered_html.startswith("<h1>") or not rendered_html.endswith("</h1>\n")

    # 2. Ensure paragraphs (<p>) exist for the body text
    assert "<p>" in rendered_html
    assert "</p>" in rendered_html

    # 3. Ensure bullet points (<ul> and <li>) exist
    assert "<ul>" in rendered_html
    assert "<li>" in rendered_html

    # 4. Ensure headings exist and are separate tags
    assert "<h3>" in rendered_html
    assert "<h4>" in rendered_html

    # 5. Ensure the body text is inside a <p> tag, not trapped inside a heading
    assert "<p>Compound interest is the interest calculated" in rendered_html or \
           "Compound interest is the interest calculated" in rendered_html and not "<h4>Compound interest is the interest" in rendered_html

def test_normal_paragraph_response():
    """Verifies that a normal conversational response or refusal renders as normal paragraphs."""
    normal_response = (
        "Based on the available financial knowledge documents in the knowledge base, "
        "I do not have enough supporting information to answer this question accurately."
    )

    formatted = format_chat_markdown(normal_response)
    rendered_html = md.render(formatted)

    # Must contain NO heading elements
    assert "<h1>" not in rendered_html
    assert "<h2>" not in rendered_html
    assert "<h3>" not in rendered_html
    assert "<h4>" not in rendered_html

    # Must be standard paragraph
    assert rendered_html.startswith("<p>")
    assert rendered_html.strip().endswith("</p>")

def test_sql_analytics_response_formatting():
    """Verifies that SQL tool responses retain their clean ### headers and list items."""
    sql_response = (
        "### 💵 Total Income Summary\n"
        "- **Total Income:** **$36,622.84**\n"
        "- **Transactions Analyzed:** 223\n"
        "- *Evidence:* Verified from database records where `transaction_type = 'income'`."
    )

    formatted = format_chat_markdown(sql_response)
    rendered_html = md.render(formatted)

    assert "<h3>" in rendered_html
    assert "Total Income Summary" in rendered_html
    assert "<ul>" in rendered_html
    assert "<li>" in rendered_html
    assert "36,622.84" in rendered_html

def test_heading_safety_guard_on_arbitrary_long_heading():
    """Verifies that an arbitrary long heading line (> 75 chars) is partitioned and not left as a giant heading."""
    long_heading_line = "# An Entire Long Paragraph Written Accidentally On A Single Heading Line That Should Not Be Rendered In Gigantic Font Because It Contains Normal Text"
    formatted = format_chat_markdown(long_heading_line)
    rendered_html = md.render(formatted)

    # Should have split into a shorter heading and a paragraph body
    assert "<p>" in rendered_html
    assert rendered_html.count("<h") >= 1
