// Google Apps Script - Save this in Google Apps Script editor
// This creates a one-click save endpoint that automatically saves to Google Sheets

function doGet(e) {
  // Get parameters from URL
  var title = e.parameter.title || 'Untitled';
  var url = e.parameter.url || '';
  var section = e.parameter.section || '';
  var summary = e.parameter.summary || '';
  var timestamp = new Date();
  
  // Open or create spreadsheet
  var spreadsheetId = '19amafV2avZFVkic49zpjHrpRB62C2hrgNwyVPOjcsxY'; // Replace with your Google Sheets ID
  var sheet = SpreadsheetApp.openById(spreadsheetId).getActiveSheet();
  
  // Add headers if this is the first row
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(['Timestamp', 'Title', 'URL', 'Section', 'Summary']);
  }
  
  // Append the new article
  sheet.appendRow([timestamp, title, url, section, summary]);
  
  // Return a simple HTML response
  var html = `
    <!DOCTYPE html>
    <html>
      <head>
        <title>Article Saved</title>
        <style>
          body {
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background-color: #f0f0f0;
          }
          .message {
            background-color: #4CAF50;
            color: white;
            padding: 20px 40px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
          }
          .close-btn {
            margin-top: 15px;
            padding: 10px 20px;
            background-color: white;
            color: #4CAF50;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
          }
        </style>
        <script>
          // Auto-close after 2 seconds
          setTimeout(function() {
            window.close();
          }, 2000);
        </script>
      </head>
      <body>
        <div class="message">
          <h2>✅ Article Saved!</h2>
          <p>${title}</p>
          <button class="close-btn" onclick="window.close()">Close</button>
        </div>
      </body>
    </html>
  `;
  
  return HtmlService.createHtmlOutput(html);
}

// Setup Instructions:
// 1. Create a new Google Apps Script project
// 2. Paste this code
// 3. Create a Google Sheet and get its ID from the URL
// 4. Replace YOUR_SPREADSHEET_ID with your sheet ID
// 5. Deploy as Web App:
//    - Execute as: Me
//    - Who has access: Anyone
// 6. Copy the deployment URL and use it in send_email.py