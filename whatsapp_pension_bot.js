const express = require('express');
const axios = require('axios');
const app = express();

// Middleware to parse JSON
app.use(express.json());

// Store for simple conversation state (in production, use a database)
const userSessions = {};

// Agent management system
const agents = {
    available: [],
    busy: {},
    tickets: {},
    collections: []
};

// Collections data for Power BI integration
const collectionsData = {
    tickets: [],
    conversations: [],
    customerInteractions: [],
    agentPerformance: [],
    responseMetrics: []
};

// WhatsApp API configuration - you'll get these from Meta
const WHATSAPP_TOKEN = process.env.WHATSAPP_TOKEN;
const PHONE_NUMBER_ID = process.env.PHONE_NUMBER_ID;
const VERIFY_TOKEN = process.env.VERIFY_TOKEN;

// Webhook verification (required by WhatsApp)
app.get('/webhook', (req, res) => {
    const mode = req.query['hub.mode'];
    const token = req.query['hub.verify_token'];
    const challenge = req.query['hub.challenge'];

    if (mode === 'subscribe' && token === VERIFY_TOKEN) {
        console.log('Webhook verified');
        res.status(200).send(challenge);
    } else {
        res.sendStatus(403);
    }
});

// Main webhook to receive messages
app.post('/webhook', (req, res) => {
    const body = req.body;

    if (body.object === 'whatsapp_business_account') {
        body.entry.forEach(entry => {
            const changes = entry.changes;
            changes.forEach(change => {
                if (change.field === 'messages') {
                    const messages = change.value.messages;
                    if (messages) {
                        messages.forEach(message => {
                            handleMessage(message, change.value.contacts[0]);
                        });
                    }
                }
            });
        });
        res.status(200).send('OK');
    } else {
        res.sendStatus(404);
    }
});

// Handle incoming messages
async function handleMessage(message, contact) {
    const from = message.from;
    const messageText = message.text?.body?.toLowerCase().trim();
    const contactName = contact.profile?.name || 'there';

    // Initialize user session if new
    if (!userSessions[from]) {
        userSessions[from] = {
            step: 'welcome',
            name: contactName,
            data: {}
        };
    }

    let response = '';
    const session = userSessions[from];

    // Main conversation flow
    switch (session.step) {
        case 'welcome':
            response = `Hello ${contactName}! 👋 Welcome to [Your Company Name] Pension Services.

I can help you with:
1️⃣ General pension information
2️⃣ Check account balance
3️⃣ Schedule a consultation
4️⃣ Contribution inquiries
5️⃣ Speak with an agent

Please reply with a number (1-5) or describe what you need help with.`;
            session.step = 'main_menu';
            break;

        case 'main_menu':
            if (messageText.includes('1') || messageText.includes('information') || messageText.includes('general')) {
                response = `📋 *Pension Information*

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

Reply with A, B, C, or D, or type "menu" to return to main options.`;
                session.step = 'pension_info';
            } else if (messageText.includes('2') || messageText.includes('balance') || messageText.includes('account')) {
                response = `🔐 *Account Balance Inquiry*

To check your account balance, I'll need to verify your identity.

Please provide:
1. Your pension ID number
2. Date of birth (DD/MM/YYYY)
3. Last 4 digits of your registered phone number

*Note: This information is kept secure and used only for verification.*`;
                session.step = 'balance_verification';
            } else if (messageText.includes('3') || messageText.includes('consultation') || messageText.includes('appointment')) {
                response = `📅 *Schedule a Consultation*

I'd be happy to help you schedule a meeting with one of our pension advisors.

Please tell me:
1. Your preferred date (DD/MM/YYYY)
2. Preferred time (morning/afternoon/evening)
3. Type of consultation needed:
   - New pension plan
   - Existing account review
   - Retirement planning
   - General advice

What works best for you?`;
                session.step = 'schedule_consultation';
            } else if (messageText.includes('4') || messageText.includes('contribution') || messageText.includes('payment')) {
                response = `💰 *Contribution Inquiries*

I can help with:
• Current contribution rates
• Payment schedules
• Increasing contributions
• Payment methods
• Contribution history

What specific information do you need about contributions?`;
                session.step = 'contribution_help';
            } else if (messageText.includes('5') || messageText.includes('agent') || messageText.includes('human')) {
                response = await handleAgentRequest(from, contactName, messageText);
                session.step = 'agent_selection';
            } else {
                response = `I'd be happy to help! Could you please choose from the options below or be more specific?

1️⃣ General pension information
2️⃣ Check account balance  
3️⃣ Schedule a consultation
4️⃣ Contribution inquiries
5️⃣ Speak with an agent

Just reply with a number or tell me what you need help with.`;
            }
            break;

        case 'pension_info':
            if (messageText.includes('a') || messageText.includes('contribution rates')) {
                response = `💵 *Contribution Rates*

Our flexible contribution options:
• Minimum: 5% of monthly salary
• Recommended: 10-15% for optimal growth
• Maximum: 25% (with tax advantages)
• Employer matching: Up to 6% (if applicable)

Current rates are competitive with market standards. Would you like to discuss a personalized contribution plan?

Reply "yes" to schedule a call, or "menu" for main options.`;
            } else if (messageText.includes('b') || messageText.includes('investment')) {
                response = `📈 *Investment Options*

We offer diversified portfolios:
• Conservative (bonds, stable income)
• Balanced (mixed bonds and equities)
• Growth (equity-focused for long-term)
• Aggressive (maximum growth potential)

All funds are professionally managed with regular performance reviews.

Would you like details on any specific option? Or type "menu" to return.`;
            } else if (messageText.includes('c') || messageText.includes('retirement benefits')) {
                response = `🏖️ *Retirement Benefits*

When you retire, you can:
• Receive monthly pension payments
• Take a partial lump sum (up to 25% tax-free)
• Transfer to another provider
• Leave benefits to beneficiaries

Benefit amounts depend on contributions and investment performance over time.

Need help calculating your potential benefits? Type "calculate" or "menu".`;
            } else if (messageText.includes('d') || messageText.includes('tax')) {
                response = `💸 *Tax Advantages*

Pension contributions offer significant tax benefits:
• Income tax relief on contributions
• Tax-free growth on investments
• Flexible withdrawal options
• Inheritance tax advantages
• Annual allowance optimization

These benefits can significantly boost your retirement savings!

Want to know your specific tax savings? Type "calculate" or "menu".`;
            } else {
                response = `Please choose one of the options:
A) Contribution rates
B) Investment options  
C) Retirement benefits
D) Tax advantages

Or type "menu" to return to main options.`;
            }
            break;

        case 'balance_verification':
            // In a real implementation, you'd verify these details against your database
            session.data.verification = messageText;
            response = `🔍 Thank you for providing your details. 

*For security reasons, account balance checks require manual verification by our team.*

I've recorded your request and someone will contact you within 2 business hours with your current balance and recent transactions.

Is there anything else I can help you with today?

Type "menu" for main options.`;
            session.step = 'main_menu';
            break;

        case 'schedule_consultation':
            session.data.consultation = messageText;
            response = `✅ Perfect! I've noted your consultation preferences:

"${messageText}"

Our team will contact you within 24 hours to confirm your appointment slot. We'll send you:
• Confirmed date and time
• Meeting location or video call link  
• Preparation checklist
• Advisor contact details

You'll receive a confirmation SMS and email shortly.

Anything else I can help with? Type "menu" for main options.`;
            session.step = 'main_menu';
            break;

        case 'contribution_help':
            response = handleContributionQuery(messageText);
            break;

        case 'agent_selection':
            response = await handleAgentSelection(from, messageText, contactName);
            break;

        case 'with_agent':
            response = await handleAgentConversation(from, messageText, contactName);
            break;

        case 'complaint_form':
            response = await handleComplaintForm(from, messageText, session);
            break;

        case 'feedback_form':
            response = await handleFeedbackForm(from, messageText, session);
            break;

        default:
            session.step = 'main_menu';
            response = `Let me help you with your pension needs. Please choose:

1️⃣ General pension information
2️⃣ Check account balance
3️⃣ Schedule a consultation  
4️⃣ Contribution inquiries
5️⃣ Speak with an agent`;
            break;
    }

    // Always offer menu option
    if (!response.includes('menu')) {
        response += '\n\n💡 Type "menu" anytime to see all options.';
    }

    // Log interaction for Power BI
    await logInteraction(from, messageText, response, session.step);

    await sendMessage(from, response);
}

// Handle contribution-related queries
function handleContributionQuery(messageText) {
    if (messageText.includes('rate') || messageText.includes('how much')) {
        return `💰 *Current Contribution Information*

Standard rates:
• Employee minimum: 5% of salary
• Employee recommended: 10-15%
• Employer contribution: Varies by company
• Self-employed: Flexible amounts

The more you contribute now, the better your retirement income will be!

Need help calculating your ideal contribution? Type "calculate".
Want to increase contributions? Type "increase".
Type "menu" for main options.`;
    } else if (messageText.includes('increase') || messageText.includes('more')) {
        return `📈 *Increase Your Contributions*

Great decision! Increasing contributions can significantly boost your retirement fund.

To increase your contributions:
1. We'll review your current rate
2. Discuss your budget and goals
3. Set up the new contribution level
4. Provide updated projections

I'll arrange for an advisor to call you within 24 hours to discuss this.

Type "menu" for other options.`;
    } else if (messageText.includes('history') || messageText.includes('past')) {
        return `📊 *Contribution History*

For detailed contribution history, our team will need to access your secure account.

We can provide:
• Monthly contribution summaries
• Annual statements
• Growth tracking
• Tax relief applied

An advisor will contact you within 2 business hours with your complete contribution history.

Type "menu" for other options.`;
    } else {
        return `I can help with various contribution topics:

• Current rates and recommendations
• Increasing your contributions
• Payment methods and schedules
• Contribution history
• Tax benefits

What specific aspect would you like to know about?`;
    }
}

// Agent Management System
async function handleAgentRequest(from, contactName, messageText) {
    const ticketId = generateTicketId();
    
    // Create initial ticket
    const ticket = {
        id: ticketId,
        customerId: from,
        customerName: contactName,
        status: 'new',
        priority: 'normal',
        createdAt: new Date().toISOString(),
        initialMessage: messageText,
        category: 'general',
        assignedAgent: null,
        messages: []
    };
    
    agents.tickets[ticketId] = ticket;
    userSessions[from].ticketId = ticketId;
    
    return `👥 *Connect with an Agent*

I'm here to connect you with the right specialist for your needs.

Please select the type of assistance you need:

1️⃣ **Account Issues** - Balance, payments, access problems
2️⃣ **Complaints** - Service issues, dissatisfaction, problems
3️⃣ **Technical Support** - App issues, login problems, errors
4️⃣ **Pension Planning** - Retirement advice, investment options
5️⃣ **Contributions** - Payment setup, increases, employer matching
6️⃣ **General Inquiry** - Other questions or information needed

🎫 Your ticket ID: *${ticketId}*

Please reply with a number (1-6) or describe your specific need.`;
}

async function handleAgentSelection(from, messageText, contactName) {
    const session = userSessions[from];
    const ticket = agents.tickets[session.ticketId];
    
    let category = 'general';
    let priority = 'normal';
    let departmentMessage = '';
    
    if (messageText.includes('1') || messageText.includes('account')) {
        category = 'account_issues';
        priority = 'high';
        departmentMessage = 'Account Services Team';
    } else if (messageText.includes('2') || messageText.includes('complaint')) {
        category = 'complaints';
        priority = 'high';
        departmentMessage = 'Customer Relations Team';
        session.step = 'complaint_form';
        return await handleComplaintForm(from, 'start', session);
    } else if (messageText.includes('3') || messageText.includes('technical')) {
        category = 'technical';
        priority = 'normal';
        departmentMessage = 'Technical Support Team';
    } else if (messageText.includes('4') || messageText.includes('planning')) {
        category = 'pension_planning';
        priority = 'normal';
        departmentMessage = 'Pension Advisory Team';
    } else if (messageText.includes('5') || messageText.includes('contribution')) {
        category = 'contributions';
        priority = 'normal';
        departmentMessage = 'Contributions Team';
    } else {
        category = 'general';
        priority = 'normal';
        departmentMessage = 'General Support Team';
    }
    
    // Update ticket
    ticket.category = category;
    ticket.priority = priority;
    ticket.department = departmentMessage;
    ticket.status = 'assigned';
    
    // Try to assign available agent
    const agent = await assignAgent(category, ticket.id);
    
    if (agent) {
        ticket.assignedAgent = agent.id;
        ticket.agentName = agent.name;
        session.step = 'with_agent';
        
        return `✅ *Connected to ${departmentMessage}*

👤 **Agent:** ${agent.name}
🎫 **Ticket ID:** ${ticket.id}
⏱️ **Status:** Connected
📞 **Response Time:** Immediate

Your agent is ready to help! Please describe your issue in detail, and ${agent.name} will assist you right away.

🔄 Type "end" to close this conversation
📋 Type "summary" for ticket details`;
    } else {
        ticket.status = 'queued';
        return `⏳ *Queued for ${departmentMessage}*

🎫 **Ticket ID:** ${ticket.id}
📊 **Priority:** ${priority.toUpperCase()}
👥 **Queue Position:** ${await getQueuePosition(category)}
⏰ **Estimated Wait:** ${await getEstimatedWait(category)}

You'll be connected to the next available agent. We'll notify you immediately when an agent becomes available.

In the meantime, you can:
• Provide more details about your issue
• Upload relevant documents (if needed)
• Type "urgent" if this requires immediate attention

💡 Type "callback" to request a phone call instead`;
    }
}

async function handleAgentConversation(from, messageText, contactName) {
    const session = userSessions[from];
    const ticket = agents.tickets[session.ticketId];
    
    if (messageText.toLowerCase() === 'end') {
        return await endAgentSession(from, ticket);
    }
    
    if (messageText.toLowerCase() === 'summary') {
        return await getTicketSummary(ticket);
    }
    
    // Log customer message
    const customerMessage = {
        sender: 'customer',
        message: messageText,
        timestamp: new Date().toISOString()
    };
    ticket.messages.push(customerMessage);
    
    // Simulate agent response (in real implementation, this would route to actual agent)
    const agentResponse = await generateAgentResponse(messageText, ticket);
    
    const agentMessage = {
        sender: 'agent',
        agentId: ticket.assignedAgent,
        message: agentResponse,
        timestamp: new Date().toISOString()
    };
    ticket.messages.push(agentMessage);
    
    return `👤 **${ticket.agentName}:** ${agentResponse}

---
🔄 Type "end" to close | 📋 "summary" for details`;
}

async function handleComplaintForm(from, messageText, session) {
    if (!session.complaint) {
        session.complaint = { step: 1 };
    }
    
    const complaint = session.complaint;
    
    switch (complaint.step) {
        case 1:
            complaint.step = 2;
            return `😔 *Complaint Registration*

I'm sorry to hear you're experiencing issues. We take all complaints seriously and will resolve this promptly.

**Step 1 of 4:** Please describe the nature of your complaint:

1️⃣ Service quality issues
2️⃣ Account/payment problems  
3️⃣ Staff behavior concerns
4️⃣ System/technical issues
5️⃣ Policy disagreements
6️⃣ Other

Please select a number or describe your complaint in detail.`;
            
        case 2:
            complaint.type = messageText;
            complaint.step = 3;
            return `📅 **Step 2 of 4:** When did this issue occur?

Please provide:
• Date of incident (DD/MM/YYYY)
• Approximate time (if relevant)
• How long has this been ongoing?

Example: "15/07/2025, around 2 PM, been ongoing for 2 weeks"`;
            
        case 3:
            complaint.dateTime = messageText;
            complaint.step = 4;
            return `📝 **Step 3 of 4:** Please provide detailed information:

• What exactly happened?
• Who was involved (if staff members)?
• What outcome are you seeking?
• Any reference numbers or previous case IDs?

The more details you provide, the better we can resolve this for you.`;
            
        case 4:
            complaint.details = messageText;
            complaint.step = 5;
            
            // Generate complaint ticket
            const complaintId = generateComplaintId();
            const complaintTicket = {
                id: complaintId,
                customerId: from,
                type: complaint.type,
                dateTime: complaint.dateTime,
                details: complaint.details,
                severity: 'medium',
                status: 'open',
                createdAt: new Date().toISOString(),
                assignedTo: 'complaints_team',
                followUpDate: new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString()
            };
            
            // Store complaint
            collectionsData.tickets.push(complaintTicket);
            
            return `✅ **Complaint Registered Successfully**

🎫 **Complaint ID:** ${complaintId}
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

Thank you for bringing this to our attention. We're committed to resolving this satisfactorily.`;
            
        default:
            session.step = 'main_menu';
            return 'Thank you for your complaint. Type "menu" to return to main options.';
    }
}

async function handleFeedbackForm(from, messageText, session) {
    // Similar structure to complaint form but for positive feedback/suggestions
    return `Thank you for your feedback! We value your input and will use it to improve our services.`;
}

// Agent assignment logic
async function assignAgent(category, ticketId) {
    // Simulate agent assignment (in real implementation, check actual agent availability)
    const availableAgents = {
        account_issues: [
            { id: 'AG001', name: 'Sarah Mitchell', speciality: 'Account Services' },
            { id: 'AG002', name: 'David Chen', speciality: 'Payment Issues' }
        ],
        complaints: [
            { id: 'AG003', name: 'Emma Johnson', speciality: 'Customer Relations' },
            { id: 'AG004', name: 'Michael Brown', speciality: 'Complaint Resolution' }
        ],
        technical: [
            { id: 'AG005', name: 'Alex Kumar', speciality: 'Technical Support' },
            { id: 'AG006', name: 'Lisa Wang', speciality: 'System Issues' }
        ],
        pension_planning: [
            { id: 'AG007', name: 'Robert Taylor', speciality: 'Pension Advisor' },
            { id: 'AG008', name: 'Jennifer Davis', speciality: 'Retirement Planning' }
        ],
        contributions: [
            { id: 'AG009', name: 'Mark Wilson', speciality: 'Contributions Specialist' },
            { id: 'AG010', name: 'Anna Garcia', speciality: 'Payment Processing' }
        ],
        general: [
            { id: 'AG011', name: 'Tom Anderson', speciality: 'General Support' }
        ]
    };
    
    const agents = availableAgents[category] || availableAgents.general;
    return agents[Math.floor(Math.random() * agents.length)];
}

async function generateAgentResponse(customerMessage, ticket) {
    // Simulate intelligent agent responses based on category and message
    const responses = {
        account_issues: [
            "I can see you're having account issues. Let me check your account details right away.",
            "I understand your concern about your account. I'm pulling up your information now.",
            "Thank you for explaining the issue. I can help resolve this account problem for you."
        ],
        complaints: [
            "I sincerely apologize for this experience. Let me escalate this to ensure it's resolved promptly.",
            "I understand your frustration, and I'm here to make this right. Let me review the details.",
            "Thank you for bringing this to our attention. I'm going to personally ensure this gets resolved."
        ],
        technical: [
            "I can help with that technical issue. Let me guide you through some troubleshooting steps.",
            "I see you're experiencing technical difficulties. Let me check our system status first.",
            "That's a common technical issue I can definitely help resolve for you."
        ]
    };
    
    const categoryResponses = responses[ticket.category] || responses.account_issues;
    return categoryResponses[Math.floor(Math.random() * categoryResponses.length)];
}

async function endAgentSession(from, ticket) {
    const session = userSessions[from];
    ticket.status = 'resolved';
    ticket.closedAt = new Date().toISOString();
    session.step = 'feedback_form';
    
    return `✅ *Session Ended*

🎫 **Ticket ID:** ${ticket.id}
👤 **Agent:** ${ticket.agentName}
⏰ **Duration:** ${calculateSessionDuration(ticket)}
📋 **Status:** Resolved

**Quick Feedback** (Optional):
How was your experience today?

1️⃣ Excellent - Issue resolved quickly
2️⃣ Good - Helpful but took some time  
3️⃣ Average - Got some help
4️⃣ Poor - Issue not fully resolved
5️⃣ Very Poor - Unsatisfactory service

Reply with a number or type "skip" to return to main menu.

Thank you for contacting us today! 😊`;
}

async function getTicketSummary(ticket) {
    return `📋 *Ticket Summary*

🎫 **ID:** ${ticket.id}
👤 **Agent:** ${ticket.agentName || 'Unassigned'}
📅 **Created:** ${formatDate(ticket.createdAt)}
📊 **Status:** ${ticket.status.toUpperCase()}
🏷️ **Category:** ${ticket.category.replace('_', ' ').toUpperCase()}
💬 **Messages:** ${ticket.messages?.length || 0}

**Latest Update:** ${ticket.messages?.slice(-1)[0]?.message?.substring(0, 100)}...

Type anything to continue conversation or "end" to close.`;
}

// Power BI Data Collection Functions
async function logInteraction(userId, userMessage, botResponse, conversationStep) {
    const interaction = {
        timestamp: new Date().toISOString(),
        userId: userId,
        userMessage: userMessage,
        botResponse: botResponse.substring(0, 200), // Truncate for storage
        conversationStep: conversationStep,
        messageType: detectMessageType(userMessage),
        responseTime: Math.floor(Math.random() * 1000), // Simulated response time
        sessionId: userSessions[userId]?.sessionId || generateSessionId()
    };
    
    collectionsData.customerInteractions.push(interaction);
    
    // Keep only last 1000 interactions to manage memory
    if (collectionsData.customerInteractions.length > 1000) {
        collectionsData.customerInteractions.shift();
    }
}

function detectMessageType(message) {
    const lowerMessage = message.toLowerCase();
    if (lowerMessage.includes('balance') || lowerMessage.includes('account')) return 'account_inquiry';
    if (lowerMessage.includes('complaint') || lowerMessage.includes('problem')) return 'complaint';
    if (lowerMessage.includes('consultation') || lowerMessage.includes('appointment')) return 'booking';
    if (lowerMessage.includes('contribution') || lowerMessage.includes('payment')) return 'contributions';
    if (lowerMessage.includes('agent') || lowerMessage.includes('human')) return 'agent_request';
    return 'general_inquiry';
}

// Power BI API Endpoints
app.get('/api/powerbi/interactions', (req, res) => {
    res.json({
        data: collectionsData.customerInteractions,
        lastUpdated: new Date().toISOString(),
        totalRecords: collectionsData.customerInteractions.length
    });
});

app.get('/api/powerbi/tickets', (req, res) => {
    const ticketArray = Object.values(agents.tickets).map(ticket => ({
        ...ticket,
        responseTimeMinutes: ticket.messages?.length > 0 ? 
            Math.floor(Math.random() * 30) : null,
        resolutionTimeHours: ticket.status === 'resolved' ? 
            Math.floor(Math.random() * 48) : null,
        customerSatisfaction: ticket.status === 'resolved' ? 
            Math.floor(Math.random() * 5) + 1 : null
    }));
    
    res.json({
        data: ticketArray,
        summary: {
            total: ticketArray.length,
            open: ticketArray.filter(t => t.status === 'open').length,
            resolved: ticketArray.filter(t => t.status === 'resolved').length,
            avgResolutionTime: 24 // hours
        }
    });
});

app.get('/api/powerbi/agent-performance', (req, res) => {
    // Generate sample agent performance data
    const agentPerformance = [
        {
            agentId: 'AG001',
            agentName: 'Sarah Mitchell',
            ticketsHandled: Math.floor(Math.random() * 50) + 10,
            avgResponseTime: Math.floor(Math.random() * 5) + 2, // minutes
            customerRating: (Math.random() * 2 + 3).toFixed(1), // 3.0-5.0
            resolutionRate: (Math.random() * 20 + 80).toFixed(1), // 80-100%
            category: 'account_issues'
        },
        {
            agentId: 'AG003',
            agentName: 'Emma Johnson',
            ticketsHandled: Math.floor(Math.random() * 45) + 15,
            avgResponseTime: Math.floor(Math.random() * 4) + 1,
            customerRating: (Math.random() * 2 + 3).toFixed(1),
            resolutionRate: (Math.random() * 15 + 85).toFixed(1),
            category: 'complaints'
        }
        // Add more agents as needed
    ];
    
    res.json({
        data: agentPerformance,
        reportPeriod: 'last_30_days',
        generatedAt: new Date().toISOString()
    });
});

app.get('/api/powerbi/conversation-analytics', (req, res) => {
    const analytics = {
        totalConversations: collectionsData.customerInteractions.length,
        avgConversationLength: 8.5, // messages
        commonIssues: [
            { issue: 'Account Balance', count: 45, percentage: '32%' },
            { issue: 'Contribution Questions', count: 28, percentage: '20%' },
            { issue: 'Technical Support', count: 21, percentage: '15%' },
            { issue: 'Complaints', count: 18, percentage: '13%' },
            { issue: 'Pension Planning', count: 15, percentage: '11%' },
            { issue: 'General Inquiry', count: 13, percentage: '9%' }
        ],
        peakHours: [
            { hour: '09:00', interactions: 25 },
            { hour: '11:00', interactions: 30 },
            { hour: '14:00', interactions: 35 },
            { hour: '16:00', interactions: 28 }
        ],
        customerSatisfaction: {
            average: 4.2,
            distribution: {
                excellent: 45,
                good: 32,
                average: 18,
                poor: 3,
                veryPoor: 2
            }
        }
    };
    
    res.json(analytics);
});

// Utility functions
function generateTicketId() {
    return 'TK' + Date.now().toString().slice(-6) + Math.random().toString(36).substr(2, 3).toUpperCase();
}

function generateComplaintId() {
    return 'CP' + Date.now().toString().slice(-6) + Math.random().toString(36).substr(2, 3).toUpperCase();
}

function generateSessionId() {
    return 'SS' + Date.now().toString() + Math.random().toString(36).substr(2, 5);
}

function formatDate(isoString) {
    return new Date(isoString).toLocaleDateString('en-GB', {
        day: '2-digit',
        month: '2-digit', 
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function calculateSessionDuration(ticket) {
    if (!ticket.closedAt) return 'Ongoing';
    const start = new Date(ticket.createdAt);
    const end = new Date(ticket.closedAt);
    const minutes = Math.floor((end - start) / (1000 * 60));
    return `${minutes} minutes`;
}

async function getQueuePosition(category) {
    // Simulate queue position
    return Math.floor(Math.random() * 5) + 1;
}

async function getEstimatedWait(category) {
    const waitTimes = {
        account_issues: '5-10 minutes',
        complaints: '2-5 minutes',
        technical: '10-15 minutes',
        pension_planning: '15-20 minutes',
        contributions: '5-10 minutes',
        general: '3-8 minutes'
    };
    return waitTimes[category] || '5-10 minutes';
}

// Send message to WhatsApp
async function sendMessage(to, message) {
    try {
        await axios.post(
            `https://graph.facebook.com/v18.0/${PHONE_NUMBER_ID}/messages`,
            {
                messaging_product: 'whatsapp',
                to: to,
                text: { body: message }
            },
            {
                headers: {
                    'Authorization': `Bearer ${WHATSAPP_TOKEN}`,
                    'Content-Type': 'application/json'
                }
            }
        );
        console.log('Message sent successfully');
    } catch (error) {
        console.error('Error sending message:', error.response?.data || error.message);
    }
}

// Basic route for health checks
app.get('/', (req, res) => {
    res.send('WhatsApp Pension Bot is running! 🤖💼');
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Bot is running on port ${PORT}`);
});

module.exports = app;