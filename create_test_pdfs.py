from fpdf import FPDF

def create_pdf(filename: str, title: str, paragraphs: list[str]):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(0, 10, text=title, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)

    pdf.set_font("Helvetica", size=11)
    for p in paragraphs:
        pdf.multi_cell(0, 7, text=p)
        pdf.ln(3)

    pdf.output(filename)
    print(f"Created {filename}")

# --- Document 1: Operating Systems & Virtual Memory ---
doc1_title = "Technical Brief: Virtual Memory and Paging Architecture"
doc1_content = [
    "Virtual memory is a memory management capability of an operating system that uses hardware and software to allow a computer to compensate for physical memory shortages, by temporarily transferring data from random access memory (RAM) to disk storage.",
    "Paging is a memory management scheme that eliminates the need for contiguous allocation of physical memory. The physical address space is broken into fixed-size blocks called frames, and logical memory is divided into blocks of the same size called pages.",
    "The Translation Lookaside Buffer (TLB) is a high-speed hardware cache used by the Memory Management Unit (MMU) to store recent translations of virtual memory to physical addresses, drastically reducing memory access latency.",
    "Page faults occur when a program attempts to access a block of memory that is not stored in the physical RAM. The operating system kernel intervenes, handles the trap, fetches the required page from secondary storage, and resumes the executing process."
]

# --- Document 2: Company Travel & Remote Work Policy ---
doc2_title = "Acme Corp: Remote Work and Travel Reimbursement Guidelines"
doc2_content = [
    "Employees eligible for remote work must maintain core working hours between 10:00 AM and 4:00 PM EST to ensure seamless team collaboration.",
    "For business-related travel, flights booked more than 14 days in advance are fully reimbursable up to a maximum cap of $850 for domestic round-trips.",
    "The daily meal allowance (per diem) during company-sponsored conferences is capped at $75 per day. Itemized receipts must be submitted via the expense portal within 30 days of trip completion.",
    "Equipment stipends: Full-time employees receive a one-time home office setup budget of $1,200 upon hire, which can be spent on monitors, ergonomic chairs, and mechanical keyboards."
]

create_pdf("virtual_memory_brief.pdf", doc1_title, doc1_content)
create_pdf("acme_remote_policy.pdf", doc2_title, doc2_content)