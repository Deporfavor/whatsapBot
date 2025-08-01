# main.py - Python WhatsApp Pension Bot
import os
import json
import asyncio
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
import httpx
import uvicorn
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="WhatsApp Pension Bot", version="6.0")

# Global storage (in production, use a database)
user_sessions = {}
agents_data = {
    "available": [],
    "busy": {},
    "tickets": {},
    "collections": []
}

collections_data = {
    "tickets": [],
    "conversations": [],
    "customer_interactions": [],
    "agent_performance": [],
    "response_metrics": []
}

# WhatsApp API configuration
WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
PHONE_NUMBER_ID = os.getenv('PHONE_NUMBER_ID')
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')

class WhatsAppMessage(BaseModel):
    object: str
    entry: List[Dict[str, Any]]

class UserSession:
    def __init__(self, step: str = 'welcome', name: str = 'there', data: Dict = None):
        self.step = step
        self.name = name
        self.data = data or {}
        self.ticket_id = None
        self.complaint = None

# Webhook verification (required by WhatsApp)
@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get('hub.mode')
    token = request.query_params.get('hub.verify_token')
    challenge = request.query_params.get('hub.challenge')
    
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        logger.info('Webhook verified')
        return PlainTextResponse(challenge)
    else:
        logger.error('Webhook verification failed')
        raise HTTPException(status_code=403, detail="Verification failed")

# Main webhook to receive messages
@app.post("/webhook")
async def handle_webhook(message: WhatsAppMessage):
    if message.object == 'whatsapp_business_account':
        for entry in message.entry:
            changes = entry.get('changes', [])
            for change in changes:
                if change.get('field') == 'messages':
                    messages = change.get('value', {}).get('messages', [])
                    contacts = change.get('value', {}).get('contacts', [])
                    
                    for msg in messages:
                        contact = contacts[0] if contacts else {}
                        await handle_message(msg, contact)
        
        return {"status": "OK"}
    else:
        raise HTTPException(status_code=404, detail="Not found")

# Handle incoming messages
async def handle_message(message: Dict, contact: Dict):
    from_number = message.get('from')
    message_text = message.get('text', {}).get('body', '').lower().strip()
    contact_name = contact.get('profile', {}).get('name', 'there')
    
    # Initialize user session if new
    if from_number not in user_sessions:
        user_sessions[from_number] = UserSession(name=contact_name)
    
    session = user_sessions[from_number]
    response = ""
    
    # Main conversation flow
    if session.step == 'welcome':
        response = f"""Hello {contact_name}! 👋 Welcome to [Your Company Name] Pension Services.

I can help you with:
1️⃣ General pension information
2️⃣ Check account balance
3️⃣ Schedule a consultation
4️⃣ Contribution inquiries
5️⃣ Speak with an agent

Please reply with a number (1-5) or describe what you need help with."""
        session.step = 'main_menu'
    
    elif session.step == 'main_menu':
        if any(word in message_text for word in ['1', 'information', 'general']):
            response = """📋 *Pension Information*

Our pension plans offer:
• Competitive returns on your investments
• Flexible contribution options
• Professional fund management
• Tax benefits and advantages
• Secure retirement planning

Would you like to know more about:
A) Contribution rates
B) Investment options
C) Retirement benefits
D) Tax advantages

Reply with A, B, C, or D, or type "menu" to return to main options."""
            session.step = 'pension_info'
            
        elif any(word in message_text for word in ['2', 'balance', 'account']):
            response = """🔐 *Account Balance Inquiry*

To check your account balance, I'll need to verify your identity.

Please provide:
1. Your pension ID number
2. Date of birth (DD/MM/YYYY)
3. Last 4 digits of your registered phone number

*Note: This information is kept secure and used only for verification.*"""
            session.step = 'balance_verification'
            
        elif any(word in message_text for word in ['3', 'consultation', 'appointment']):
            response = """📅 *Schedule a Consultation*

I'd be happy to help you schedule a meeting with one of our pension advisors.

Please tell me:
1. Your preferred date (DD/MM/YYYY)
2. Preferred time (morning/afternoon/evening)
3. Type of consultation needed:
   - New pension plan
   - Existing account review
   - Retirement planning
   - General advice

What works best for you?"""
            session.step = 'schedule_consultation'
            
        elif any(word in message_text for word in ['4', 'contribution', 'payment']):
            response = """💰 *Contribution Inquiries*

I can help with:
• Current contribution rates
• Payment schedules
• Increasing contributions
• Payment methods
• Contribution history

What specific information do you need about contributions?"""
            session.step = 'contribution_help'
            
        elif any(word in message_text for word in ['5', 'agent', 'human']):
            response = await handle_agent_request(from_number, contact_name, message_text)
            session.step = 'agent_selection'
            
        else:
            response = """I'd be happy to help! Could you please choose from the options below or be more specific?

1️⃣ General pension information
2️⃣ Check account balance  
3️⃣ Schedule a consultation
4️⃣ Contribution inquiries
5️⃣ Speak with an agent

Just reply with a number or tell me what you need help with."""
    
    elif session.step == 'pension_info':
        if any(word in message_text for word in ['a', 'contribution rates']):
            response = """💵 *Contribution Rates*

Our flexible contribution options:
• Minimum: 5% of monthly salary
• Recommended: 10-15% for optimal growth
• Maximum: 25% (with tax advantages)
• Employer matching: Up to 6% (if applicable)

Current rates are competitive with market standards. Would you like to discuss a personalized contribution plan?

Reply "yes" to schedule a call, or "menu" for main options."""
            
        elif any(word in message_text for word in ['b', 'investment']):
            response = """📈 *Investment Options*

We offer diversified portfolios:
• Conservative (bonds, stable income)
• Balanced (mixed bonds and equities)
• Growth (equity-focused for long-term)
• Aggressive (maximum growth potential)

All funds are professionally managed with regular performance reviews.

Would you like details on any specific option? Or type "menu" to return."""
            
        elif any(word in message_text for word in ['c', 'retirement benefits']):
            response = """🏖️ *Retirement Benefits*

When you retire, you can:
• Receive monthly pension payments
• Take a partial lump sum (up to 25% tax-free)
• Transfer to another provider
• Leave benefits to beneficiaries

Benefit amounts depend on contributions and investment performance over time.

Need help calculating your potential benefits? Type "calculate" or "menu"."""
            
        elif any(word in message_text for word in ['d', 'tax']):
            response = """💸 *Tax Advantages*

Pension contributions offer significant tax benefits:
• Income tax relief on contributions
• Tax-free growth on investments
• Flexible withdrawal options
• Inheritance tax advantages
• Annual allowance optimization

These benefits can significantly boost your retirement savings!

Want to know your specific tax savings? Type "calculate" or "menu"."""
            
        else:
            response = """Please choose one of the options:
A) Contribution rates
B) Investment options  
C) Retirement benefits
D) Tax advantages

Or type "menu" to return to main options."""
    
    elif session.step == 'balance_verification':
        session.data['verification'] = message_text
        response = """🔍 Thank you for providing your details. 

*For security reasons, account balance checks require manual verification by our team.*

I've recorded your request and someone will contact you within 2 business hours with your current balance and recent transactions.

Is there anything else I can help you with today?

Type "menu" for main options."""
        session.step = 'main_menu'
    
    elif session.step == 'schedule_consultation':
        session.data['consultation'] = message_text
        response = f"""✅ Perfect! I've noted your consultation preferences:

"{message_text}"

Our team will contact you within 24 hours to confirm your appointment slot. We'll send you:
• Confirmed date and time
• Meeting location or video call link  
• Preparation checklist
• Advisor contact details

You'll receive a confirmation SMS and email shortly.

Anything else I can help with? Type "menu" for main options."""
        session.step = 'main_menu'
    
    elif session.step == 'contribution_help':
        response = handle_contribution_query(message_text)
    
    elif session.step == 'agent_selection':
        response = await handle_agent_selection(from_number, message_text, contact_name)
    
    elif session.step == 'with_agent':
        response = await handle_agent_conversation(from_number, message_text, contact_name)
    
    elif session.step == 'complaint_form':
        response = await handle_complaint_form(from_number, message_text, session)
    
    elif session.step == 'feedback_form':
        response = await handle_feedback_form(from_number, message_text, session)
    
    else:
        session.step = 'main_menu'
        response = """Let me help you with your pension needs. Please choose:

1️⃣ General pension information
2️⃣ Check account balance
3️⃣ Schedule a consultation  
4️⃣ Contribution inquiries
5️⃣ Speak with an agent"""
    
    # Always offer menu option
    if 'menu' not in response:
        response += '\n\n💡 Type "menu" anytime to see all options.'
    
    # Log interaction for Power BI
    await log_interaction(from_number, message_text, response, session.step)
    
    await send_message(from_number, response)

# Handle contribution-related queries
def handle_contribution_query(message_text: str) -> str:
    if any(word in message_text for word in ['rate', 'how much']):
        return """💰 *Current Contribution Information*

Standard rates:
• Employee minimum: 5% of salary
• Employee recommended: 10-15%
• Employer contribution: Varies by company
• Self-employed: Flexible amounts

The more you contribute now, the better your retirement income will be!

Need help calculating your ideal contribution? Type "calculate".
Want to increase contributions? Type "increase".
Type "menu" for main options."""
        
    elif any(word in message_text for word in ['increase', 'more']):
        return """📈 *Increase Your Contributions*

Great decision! Increasing contributions can significantly boost your retirement fund.

To increase your contributions:
1. We'll review your current rate
2. Discuss your budget and goals
3. Set up the new contribution level
4. Provide updated projections

I'll arrange for an advisor to call you within 24 hours to discuss this.

Type "menu" for other options."""
        
    elif any(word in message_text for word in ['history', 'past']):
        return """📊 *Contribution History*

For detailed contribution history, our team will need to access your secure account.

We can provide:
• Monthly contribution summaries
• Annual statements
• Growth tracking
• Tax relief applied

An advisor will contact you within 2 business hours with your complete contribution history.

Type "menu" for other options."""
        
    else:
        return """I can help with various contribution topics:

• Current rates and recommendations
• Increasing your contributions
• Payment methods and schedules
• Contribution history
• Tax benefits

What specific aspect would you like to know about?"""

# Agent Management System
async def handle_agent_request(from_number: str, contact_name: str, message_text: str) -> str:
    ticket_id = generate_ticket_id()
    
    # Create initial ticket
    ticket = {
        'id': ticket_id,
        'customer_id': from_number,
        'customer_name': contact_name,
        'status': 'new',
        'priority': 'normal',
        'created_at': datetime.now().isoformat(),
        'initial_message': message_text,
        'category': 'general',
        'assigned_agent': None,
        'messages': []
    }
    
    agents_data['tickets'][ticket_id] = ticket
    user_sessions[from_number].ticket_id = ticket_id
    
    return f"""👥 *Connect with an Agent*

I'm here to connect you with the right specialist for your needs.

Please select the type of assistance you need:

1️⃣ **Account Issues** - Balance, payments, access problems
2️⃣ **Complaints** - Service issues, dissatisfaction, problems
3️⃣ **Technical Support** - App issues, login problems, errors
4️⃣ **Pension Planning** - Retirement advice, investment options
5️⃣ **Contributions** - Payment setup, increases, employer matching
6️⃣ **General Inquiry** - Other questions or information needed

🎫 Your ticket ID: *{ticket_id}*

Please reply with a number (1-6) or describe your specific need."""

async def handle_agent_selection(from_number: str, message_text: str, contact_name: str) -> str:
    session = user_sessions[from_number]
    ticket = agents_data['tickets'][session.ticket_id]
    
    category = 'general'
    priority = 'normal'
    department_message = ''
    
    if any(word in message_text for word in ['1', 'account']):
        category = 'account_issues'
        priority = 'high'
        department_message = 'Account Services Team'
    elif any(word in message_text for word in ['2', 'complaint']):
        category = 'complaints'
        priority = 'high'
        department_message = 'Customer Relations Team'
        session.step = 'complaint_form'
        return await handle_complaint_form(from_number, 'start', session)
    elif any(word in message_text for word in ['3', 'technical']):
        category = 'technical'
        priority = 'normal'
        department_message = 'Technical Support Team'
    elif any(word in message_text for word in ['4', 'planning']):
        category = 'pension_planning'
        priority = 'normal'
        department_message = 'Pension Advisory Team'
    elif any(word in message_text for word in ['5', 'contribution']):
        category = 'contributions'
        priority = 'normal'
        department_message = 'Contributions Team'
    else:
        category = 'general'
        priority = 'normal'
        department_message = 'General Support Team'
    
    # Update ticket
    ticket['category'] = category
    ticket['priority'] = priority
    ticket['department'] = department_message
    ticket['status'] = 'assigned'
    
    # Try to assign available agent
    agent = await assign_agent(category, ticket['id'])
    
    if agent:
        ticket['assigned_agent'] = agent['id']
        ticket['agent_name'] = agent['name']
        session.step = 'with_agent'
        
        return f"""✅ *Connected to {department_message}*

👤 **Agent:** {agent['name']}
🎫 **Ticket ID:** {ticket['id']}
⏱️ **Status:** Connected
📞 **Response Time:** Immediate

Your agent is ready to help! Please describe your issue in detail, and {agent['name']} will assist you right away.

🔄 Type "end" to close this conversation
📋 Type "summary" for ticket details"""
    else:
        ticket['status'] = 'queued'
        queue_position = await get_queue_position(category)
        estimated_wait = await get_estimated_wait(category)
        
        return f"""⏳ *Queued for {department_message}*

🎫 **Ticket ID:** {ticket['id']}
📊 **Priority:** {priority.upper()}
👥 **Queue Position:** {queue_position}
⏰ **Estimated Wait:** {estimated_wait}

You'll be connected to the next available agent. We'll notify you immediately when an agent becomes available.

In the meantime, you can:
• Provide more details about your issue
• Upload relevant documents (if needed)
• Type "urgent" if this requires immediate attention

💡 Type "callback" to request a phone call instead"""

async def handle_agent_conversation(from_number: str, message_text: str, contact_name: str) -> str:
    session = user_sessions[from_number]
    ticket = agents_data['tickets'][session.ticket_id]
    
    if message_text.lower() == 'end':
        return await end_agent_session(from_number, ticket)
    
    if message_text.lower() == 'summary':
        return await get_ticket_summary(ticket)
    
    # Log customer message
    customer_message = {
        'sender': 'customer',
        'message': message_text,
        'timestamp': datetime.now().isoformat()
    }
    ticket['messages'].append(customer_message)
    
    # Simulate agent response
    agent_response = await generate_agent_response(message_text, ticket)
    
    agent_message = {
        'sender': 'agent',
        'agent_id': ticket['assigned_agent'],
        'message': agent_response,
        'timestamp': datetime.now().isoformat()
    }
    ticket['messages'].append(agent_message)
    
    return f"""👤 **{ticket['agent_name']}:** {agent_response}

---
🔄 Type "end" to close | 📋 "summary" for details"""

async def handle_complaint_form(from_number: str, message_text: str, session: UserSession) -> str:
    if not session.complaint:
        session.complaint = {'step': 1}
    
    complaint = session.complaint
    
    if complaint['step'] == 1:
        complaint['step'] = 2
        return """😔 *Complaint Registration*

I'm sorry to hear you're experiencing issues. We take all complaints seriously and will resolve this promptly.

**Step 1 of 4:** Please describe the nature of your complaint:

1️⃣ Service quality issues
2️⃣ Account/payment problems  
3️⃣ Staff behavior concerns
4️⃣ System/technical issues
5️⃣ Policy disagreements
6️⃣ Other

Please select a number or describe your complaint in detail."""
        
    elif complaint['step'] == 2:
        complaint['type'] = message_text
        complaint['step'] = 3
        return """📅 **Step 2 of 4:** When did this issue occur?

Please provide:
• Date of incident (DD/MM/YYYY)
• Approximate time (if relevant)
• How long has this been ongoing?

Example: "15/07/2025, around 2 PM, been ongoing for 2 weeks" """
        
    elif complaint['step'] == 3:
        complaint['date_time'] = message_text
        complaint['step'] = 4
        return """📝 **Step 3 of 4:** Please provide detailed information:

• What exactly happened?
• Who was involved (if staff members)?
• What outcome are you seeking?
• Any reference numbers or previous case IDs?

The more details you provide, the better we can resolve this for you."""
        
    elif complaint['step'] == 4:
        complaint['details'] = message_text
        complaint['step'] = 5
        
        # Generate complaint ticket
        complaint_id = generate_complaint_id()
        complaint_ticket = {
            'id': complaint_id,
            'customer_id': from_number,
            'type': complaint['type'],
            'date_time': complaint['date_time'],
            'details': complaint['details'],
            'severity': 'medium',
            'status': 'open',
            'created_at': datetime.now().isoformat(),
            'assigned_to': 'complaints_team',
            'follow_up_date': (datetime.now() + timedelta(hours=48)).isoformat()
        }
        
        # Store complaint
        collections_data['tickets'].append(complaint_ticket)
        
        return f"""✅ **Complaint Registered Successfully**

🎫 **Complaint ID:** {complaint_id}
📋 **Status:** Under Investigation  
👥 **Assigned to:** Customer Relations Manager
⏰ **Response Time:** Within 48 hours
📞 **Follow-up:** We'll contact you within 2 business days

**Step 4 of 4:** How would you like us to contact you with updates?

1️⃣ WhatsApp messages (this number)
2️⃣ Phone call
3️⃣ Email
4️⃣ SMS updates

**What happens next:**
✓ Investigation begins immediately
✓ Manager review within 24 hours  
✓ Resolution plan within 48 hours
✓ Follow-up until resolved

Thank you for bringing this to our attention. We're committed to resolving this satisfactorily."""
        
    else:
        session.step = 'main_menu'
        return 'Thank you for your complaint. Type "menu" to return to main options.'

async def handle_feedback_form(from_number: str, message_text: str, session: UserSession) -> str:
    return "Thank you for your feedback! We value your input and will use it to improve our services."

# Agent assignment logic
async def assign_agent(category: str, ticket_id: str) -> Optional[Dict]:
    available_agents = {
        'account_issues': [
            {'id': 'AG001', 'name': 'Sarah Mitchell', 'speciality': 'Account Services'},
            {'id': 'AG002', 'name': 'David Chen', 'speciality': 'Payment Issues'}
        ],
        'complaints': [
            {'id': 'AG003', 'name': 'Emma Johnson', 'speciality': 'Customer Relations'},
            {'id': 'AG004', 'name': 'Michael Brown', 'speciality': 'Complaint Resolution'}
        ],
        'technical': [
            {'id': 'AG005', 'name': 'Alex Kumar', 'speciality': 'Technical Support'},
            {'id': 'AG006', 'name': 'Lisa Wang', 'speciality': 'System Issues'}
        ],
        'pension_planning': [
            {'id': 'AG007', 'name': 'Robert Taylor', 'speciality': 'Pension Advisor'},
            {'id': 'AG008', 'name': 'Jennifer Davis', 'speciality': 'Retirement Planning'}
        ],
        'contributions': [
            {'id': 'AG009', 'name': 'Mark Wilson', 'speciality': 'Contributions Specialist'},
            {'id': 'AG010', 'name': 'Anna Garcia', 'speciality': 'Payment Processing'}
        ],
        'general': [
            {'id': 'AG011', 'name': 'Tom Anderson', 'speciality': 'General Support'}
        ]
    }
    
    agents = available_agents.get(category, available_agents['general'])
    return random.choice(agents)

async def generate_agent_response(customer_message: str, ticket: Dict) -> str:
    responses = {
        'account_issues': [
            "I can see you're having account issues. Let me check your account details right away.",
            "I understand your concern about your account. I'm pulling up your information now.",
            "Thank you for explaining the issue. I can help resolve this account problem for you."
        ],
        'complaints': [
            "I sincerely apologize for this experience. Let me escalate this to ensure it's resolved promptly.",
            "I understand your frustration, and I'm here to make this right. Let me review the details.",
            "Thank you for bringing this to our attention. I'm going to personally ensure this gets resolved."
        ],
        'technical': [
            "I can help with that technical issue. Let me guide you through some troubleshooting steps.",
            "I see you're experiencing technical difficulties. Let me check our system status first.",
            "That's a common technical issue I can definitely help resolve for you."
        ]
    }
    
    category_responses = responses.get(ticket['category'], responses['account_issues'])
    return random.choice(category_responses)

async def end_agent_session(from_number: str, ticket: Dict) -> str:
    session = user_sessions[from_number]
    ticket['status'] = 'resolved'
    ticket['closed_at'] = datetime.now().isoformat()
    session.step = 'feedback_form'
    
    return f"""✅ *Session Ended*

🎫 **Ticket ID:** {ticket['id']}
👤 **Agent:** {ticket['agent_name']}
⏰ **Duration:** {calculate_session_duration(ticket)}
📋 **Status:** Resolved

**Quick Feedback** (Optional):
How was your experience today?

1️⃣ Excellent - Issue resolved quickly
2️⃣ Good - Helpful but took some time  
3️⃣ Average - Got some help
4️⃣ Poor - Issue not fully resolved
5️⃣ Very Poor - Unsatisfactory service

Reply with a number or type "skip" to return to main menu.

Thank you for contacting us today! 😊"""

async def get_ticket_summary(ticket: Dict) -> str:
    latest_message = ""
    if ticket['messages']:
        latest_message = ticket['messages'][-1]['message'][:100] + "..."
    
    return f"""📋 *Ticket Summary*

🎫 **ID:** {ticket['id']}
👤 **Agent:** {ticket.get('agent_name', 'Unassigned')}
📅 **Created:** {format_date(ticket['created_at'])}
📊 **Status:** {ticket['status'].upper()}
🏷️ **Category:** {ticket['category'].replace('_', ' ').upper()}
💬 **Messages:** {len(ticket.get('messages', []))}

**Latest Update:** {latest_message}

Type anything to continue conversation or "end" to close."""

# Power BI Data Collection Functions
async def log_interaction(user_id: str, user_message: str, bot_response: str, conversation_step: str):
    interaction = {
        'timestamp': datetime.now().isoformat(),
        'user_id': user_id,
        'user_message': user_message,
        'bot_response': bot_response[:200],  # Truncate for storage
        'conversation_step': conversation_step,
        'message_type': detect_message_type(user_message),
        'response_time': random.randint(500, 2500),  # Simulated response time
        'session_id': generate_session_id()
    }
    
    collections_data['customer_interactions'].append(interaction)
    
    # Keep only last 1000 interactions to manage memory
    if len(collections_data['customer_interactions']) > 1000:
        collections_data['customer_interactions'].pop(0)

def detect_message_type(message: str) -> str:
    lower_message = message.lower()
    if any(word in lower_message for word in ['balance', 'account']):
        return 'account_inquiry'
    if any(word in lower_message for word in ['complaint', 'problem']):
        return 'complaint'
    if any(word in lower_message for word in ['consultation', 'appointment']):
        return 'booking'
    if any(word in lower_message for word in ['contribution', 'payment']):
        return 'contributions'
    if any(word in lower_message for word in ['agent', 'human']):
        return 'agent_request'
    return 'general_inquiry'

# Power BI API Endpoints
@app.get("/api/powerbi/interactions")
async def get_interactions():
    return {
        "data": collections_data['customer_interactions'],
        "lastUpdated": datetime.now().isoformat(),
        "totalRecords": len(collections_data['customer_interactions'])
    }

@app.get("/api/powerbi/tickets")
async def get_tickets():
    ticket_array = []
    for ticket in agents_data['tickets'].values():
        ticket_data = dict(ticket)
        ticket_data['response_time_minutes'] = random.randint(5, 30) if ticket_data.get('messages') else None
        ticket_data['resolution_time_hours'] = random.randint(1, 48) if ticket_data['status'] == 'resolved' else None
        ticket_data['customer_satisfaction'] = random.randint(1, 5) if ticket_data['status'] == 'resolved' else None
        ticket_array.append(ticket_data)
    
    return {
        "data": ticket_array,
        "summary": {
            "total": len(ticket_array),
            "open": len([t for t in ticket_array if t['status'] == 'open']),
            "resolved": len([t for t in ticket_array if t['status'] == 'resolved']),
            "avgResolutionTime": 24  # hours
        }
    }

@app.get("/api/powerbi/agent-performance")
async def get_agent_performance():
    agent_performance = [
        {
            "agentId": "AG001",
            "agentName": "Sarah Mitchell",
            "ticketsHandled": random.randint(10, 60),
            "avgResponseTime": random.randint(2, 7),  # minutes
            "customerRating": round(random.uniform(3.0, 5.0), 1),  # 3.0-5.0
            "resolutionRate": round(random.uniform(80, 100), 1),  # 80-100%
            "category": "account_issues"
        },
        {
            "agentId": "AG003",
            "agentName": "Emma Johnson",
            "ticketsHandled": random.randint(15, 60),
            "avgResponseTime": random.randint(1, 5),
            "customerRating": round(random.uniform(3.0, 5.0), 1),
            "resolutionRate": round(random.uniform(85, 100), 1),
            "category": "complaints"
        }
    ]
    
    return {
        "data": agent_performance,
        "reportPeriod": "last_30_days",
        "generatedAt": datetime.now().isoformat()
    }

@app.get("/api/powerbi/conversation-analytics")
async def get_conversation_analytics():
    analytics = {
        "totalConversations": len(collections_data['customer_interactions']),
        "avgConversationLength": 8.5,  # messages
        "commonIssues": [
            {"issue": "Account Balance", "count": 45, "percentage": "32%"},
            {"issue": "Contribution Questions", "count": 28, "percentage": "20%"},
            {"issue": "Technical Support", "count": 21, "percentage": "15%"},
            {"issue": "Complaints", "count": 18, "percentage": "13%"},
            {"issue": "Pension Planning", "count": 15, "percentage": "11%"},
            {"issue": "General Inquiry", "count": 13, "percentage": "9%"}
        ],
        "peakHours": [
            {"hour": "09:00", "interactions": 25},
            {"hour": "11:00", "interactions": 30},
            {"hour": "14:00", "interactions": 35},
            {"hour": "16:00", "interactions": 28}
        ],
        "customerSatisfaction": {
            "average": 4.2,
            "distribution": {
                "excellent": 45,
                "good": 32,
                "average": 18,
                "poor": 3,
                "veryPoor": 2
            }
        }
    }
    
    return analytics

# Utility functions
def generate_ticket_id() -> str:
    timestamp = str(int(datetime.now().timestamp()))[-6:]
    random_part = ''.join(random.choices(string.ascii_uppercase, k=3))
    return f"TK{timestamp}{random_part}"

def generate_complaint_id() -> str:
    timestamp = str(int(datetime.now().timestamp()))[-6:]
    random_part = ''.join(random.choices(string.ascii_uppercase, k=3))
    return f"CP{timestamp}{random_part}"

def generate_session_id() -> str:
    timestamp = str(int(datetime.now().timestamp()))
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
    return f"SS{timestamp}{random_part}"

def format_date(iso_string: str) -> str:
    dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
    return dt.strftime('%d/%m/%Y %H:%M')

def calculate_session_duration(ticket: Dict) -> str:
    if 'closed_at' not in ticket:
        return 'Ongoing'
    
    start = datetime.fromisoformat(ticket['created_at'])
    end = datetime.fromisoformat(ticket['closed_at'])
    duration = end - start
    minutes = int(duration.total_seconds() / 60)
    return f"{minutes} minutes"

async def get_queue_position(category: str) -> int:
    return random.randint(1, 6)

async def get_estimated_wait(category: str) -> str:
    wait_times = {
        'account_issues': '5-10 minutes',
        'complaints': '2-5 minutes',
        'technical': '10-15 minutes',
        'pension_planning': '15-20 minutes',
        'contributions': '5-10 minutes',
        'general': '3-8 minutes'
    }
    return wait_times.get(category, '5-10 minutes')

# Send message to WhatsApp
async def send_message(to: str, message: str):
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        logger.warning("WhatsApp credentials not configured")
        return
    
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": message}
    }
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            logger.info(f"Message sent successfully to {to}")
    except httpx.HTTPError as e:
        logger.error(f"Error sending WhatsApp message: {e}")
    except Exception as e:
        logger.error(f"Unexpected error sending message: {e}")

# Health check endpoint
@app.get("/")
async def health_check():
    return {"message": "WhatsApp Pension Bot is running! 🤖💼"}

@app.get("/health")
async def detailed_health():
    return {
        "status": "healthy",
        "service": "WhatsApp Pension Bot",
        "version": "6.0",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(user_sessions),
        "total_tickets": len(agents_data['tickets']),
        "total_interactions": len(collections_data['customer_interactions'])
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)