// Background Service Worker
// Coordinates data between content scripts, popup, and native messaging host

console.log('[KB Assist] Background service worker initialized');

// Handle extension installation - open setup page on first install
chrome.runtime.onInstalled.addListener((details) => {
    if (details.reason === 'install') {
        console.log('[KB Assist] First install - opening setup page');
        chrome.tabs.create({
            url: chrome.runtime.getURL('setup.html')
        });
    } else if (details.reason === 'update') {
        console.log('[KB Assist] Extension updated');
        // Check if setup was completed in old version
        chrome.storage.local.get(['setup_completed'], (result) => {
            if (!result.setup_completed) {
                // Open setup if not completed
                chrome.tabs.create({
                    url: chrome.runtime.getURL('setup.html')
                });
            }
        });
    }
});

// Listen for messages from content scripts, popup, and bridge page
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('[KB Assist] Background received message:', request.type);

    switch (request.type) {
        case 'D365_DATA_SCRAPED':
            handleD365DataScraped(request.data);
            sendResponse({ success: true });
            break;

        case 'KB_DATA_SCRAPED':
            handleKBDataScraped(request.data);
            sendResponse({ success: true });
            break;

        case 'SUBMIT_REPORT':
            handleSubmitReport(request.data, sendResponse);
            return true; // Keep channel open for async response

        case 'GET_SCRAPED_DATA':
            handleGetScrapedData(sendResponse);
            return true; // Keep channel open for async response

        case 'SUBMIT_SUCCESS':
            if (sender.tab) {
                console.log('[KB Assist] Received success from bridge page:', request);
                const callback = pendingSubmissions.get(sender.tab.id);
                if (callback) {
                    // Clear scraped data after successful submission
                    chrome.storage.local.remove(['d365_case_data', 'kb_article_data']);
                    chrome.action.setBadgeText({ text: '' });

                    callback({
                        success: true,
                        reportId: request.reportId
                    });

                    pendingSubmissions.delete(sender.tab.id);
                }
                // Close the bridge tab
                chrome.tabs.remove(sender.tab.id);
            }
            break;

        case 'SUBMIT_ERROR':
            if (sender.tab) {
                console.error('[KB Assist] Received error from bridge page:', request);
                const callback = pendingSubmissions.get(sender.tab.id);
                if (callback) {
                    callback({
                        success: false,
                        error: request.error
                    });

                    pendingSubmissions.delete(sender.tab.id);
                }
                // Close the bridge tab after a delay
                setTimeout(() => {
                    chrome.tabs.remove(sender.tab.id);
                }, 3000);
            }
            break;

        default:
            console.log('[KB Assist] Unknown message type:', request.type);
            sendResponse({ success: false, error: 'Unknown message type' });
    }
});

/**
 * Handle D365 data scraped from content script
 */
function handleD365DataScraped(data) {
    console.log('[KB Assist] D365 data received:', data);

    // Update badge to indicate data is available
    if (data.scraped) {
        chrome.action.setBadgeText({ text: '✓' });
        chrome.action.setBadgeBackgroundColor({ color: '#28a745' });
    }
}

/**
 * Handle KB data scraped from content script
 */
function handleKBDataScraped(data) {
    console.log('[KB Assist] KB data received:', data);

    // Update badge to indicate KB data is available
    if (data.scraped) {
        chrome.action.setBadgeText({ text: 'KB' });
        chrome.action.setBadgeBackgroundColor({ color: '#d71921' });
    }
}

/**
 * Get all scraped data from storage
 */
function handleGetScrapedData(sendResponse) {
    chrome.storage.local.get(['d365_case_data', 'kb_article_data'], (result) => {
        console.log('[KB Assist] Retrieved scraped data:', result);
        sendResponse({
            success: true,
            d365Data: result.d365_case_data || {},
            kbData: result.kb_article_data || {}
        });
    });
}

/**
 * Submit report to API server
 * CONFIGURATION: Set your API server URL below
 */
async function handleSubmitReport(reportData, sendResponse) {
    console.log('[KB Assist] Submitting report:', reportData);

    // ============================================
    // CONFIGURE THIS: Set your API server URL
    // ============================================
    // RENDER.COM DEPLOYMENT (Live Production URL)
    const API_URL = 'https://kb-assist-api.onrender.com/submit';

    // OLD DEPLOYMENTS (archived):
    // const API_URL = 'https://kb-assist-api-adriane-bfb3dzbvajg7fmb4.eastus-01.azurewebsites.net/submit'; // Old Azure
    // const API_URL = 'https://stephine-overinterested-xander.ngrok-free.dev/submit'; // Old ngrok

    // OPTION 2: Local testing (extension and API on same machine)
    // Uncomment this line if testing locally:
    // const API_URL = 'http://localhost:5000/submit';

    // NOTE: Now using PostgreSQL via Neon.tech (deployed on Render.com)
    // Data goes: Extension → Render API → PostgreSQL → Streamlit Dashboard
    // ============================================

    console.log('[KB Assist] Sending to API:', API_URL);

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(reportData)
        });

        console.log('[KB Assist] Response status:', response.status);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log('[KB Assist] Response data:', data);

        if (data.success) {
            // Clear scraped data after successful submission
            chrome.storage.local.remove(['d365_case_data', 'kb_article_data']);
            chrome.action.setBadgeText({ text: '' });

            sendResponse({
                success: true,
                report_id: data.report_id,
                request_id: data.request_id,  // ADD THIS
                status: data.status,  // ADD THIS
                ai_validation: data.ai_validation  // ADD THIS
            });
        } else {
            sendResponse({
                success: false,
                error: data.error || 'Unknown server error'
            });
        }

    } catch (error) {
        console.error('[KB Assist] Error:', error);
        sendResponse({
            success: false,
            error: `Cannot connect to API server at ${API_URL}. Make sure START_WINDOWS.bat is running on your physical machine. Error: ${error.message}`
        });
    }

    return true; // Keep channel open for async response
}

// Track pending submissions by tab ID
const pendingSubmissions = new Map();

/**
 * Handle extension installation
 */
chrome.runtime.onInstalled.addListener((details) => {
    if (details.reason === 'install') {
        console.log('[KB Assist] Extension installed');

        // Set default engineer info if available
        chrome.identity.getProfileUserInfo((userInfo) => {
            if (userInfo.email) {
                chrome.storage.local.set({
                    engineer_email: userInfo.email,
                    engineer_name: userInfo.email.split('@')[0].replace('.', ' ')
                });
            }
        });
    } else if (details.reason === 'update') {
        console.log('[KB Assist] Extension updated');
    }
});

/**
 * Clear badge when popup is opened
 */
chrome.action.onClicked.addListener(() => {
    console.log('[KB Assist] Extension icon clicked');
});

console.log('[KB Assist] Background service worker ready');
