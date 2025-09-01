/**
 * Lottery GUI JavaScript Application
 * Modern, clean interface for lottery management
 */

class LotteryApp {
    constructor() {
        this.currentState = 'input';
        this.lotteryData = null;
        this.winners = [];
        
        this.initializeElements();
        this.bindEvents();
        this.loadInitialState();
    }
    
    initializeElements() {
        // Sections
        this.inputSection = document.getElementById('input-section');
        this.configSection = document.getElementById('config-section');
        this.drawingSection = document.getElementById('drawing-section');
        this.resultsSection = document.getElementById('results-section');
        
        // Tab elements
        this.tabBtns = document.querySelectorAll('.tab-btn');
        this.tabContents = document.querySelectorAll('.tab-content');
        
        // Upload elements
        this.uploadArea = document.getElementById('upload-area');
        this.fileInput = document.getElementById('file-input');
        this.fileSelectBtn = document.getElementById('file-select-btn');
        
        // Manual entry elements
        this.winnersCountInput = document.getElementById('winners-count');
        this.entriesTextarea = document.getElementById('entries-text');
        this.manualSubmitBtn = document.getElementById('manual-submit-btn');
        
        // Configuration elements
        this.configStats = document.getElementById('config-stats');
        this.shuffleBtn = document.getElementById('shuffle-btn');
        this.resetBtn = document.getElementById('reset-btn');
        this.randomizationInputs = document.querySelectorAll('input[name="randomization"]');
        
        // Drawing elements
        this.drawProgress = document.getElementById('draw-progress');
        this.drawWinnerBtn = document.getElementById('draw-winner-btn');
        this.currentWinner = document.getElementById('current-winner');
        
        // Results elements
        this.resultsStats = document.getElementById('results-stats');
        this.winnersList = document.getElementById('winners-list');
        this.exportBtn = document.getElementById('export-btn');
        this.newLotteryBtn = document.getElementById('new-lottery-btn');
        
        // Overlay and notifications
        this.loadingOverlay = document.getElementById('loading-overlay');
        this.notificationContainer = document.getElementById('notification-container');
    }
    
    bindEvents() {
        // Tab switching
        this.tabBtns.forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });
        
        // File upload
        this.fileSelectBtn.addEventListener('click', () => this.fileInput.click());
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        
        // Drag and drop
        this.uploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.uploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.uploadArea.addEventListener('drop', (e) => this.handleFileDrop(e));
        this.uploadArea.addEventListener('click', () => this.fileInput.click());
        
        // Manual entry
        this.manualSubmitBtn.addEventListener('click', () => this.submitManualEntries());
        
        // Configuration
        this.shuffleBtn.addEventListener('click', () => this.shuffleLottery());
        this.resetBtn.addEventListener('click', () => this.resetLottery());
        
        // Drawing
        this.drawWinnerBtn.addEventListener('click', () => this.drawNextWinner());
        
        // Results
        this.exportBtn.addEventListener('click', () => this.exportResults());
        this.newLotteryBtn.addEventListener('click', () => this.resetLottery());
    }
    
    async loadInitialState() {
        try {
            const response = await this.apiCall('/api/status');
            if (response.entry_count > 0) {
                this.lotteryData = response;
                this.updateUI();
            }
        } catch (error) {
            console.log('No existing lottery state');
        }
    }
    
    // Tab Management
    switchTab(tabName) {
        // Update tab buttons
        this.tabBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });
        
        // Update tab content
        this.tabContents.forEach(content => {
            content.classList.toggle('active', content.id === `${tabName}-tab`);
        });
    }
    
    // File Upload Handling
    handleDragOver(e) {
        e.preventDefault();
        this.uploadArea.classList.add('drag-over');
    }
    
    handleDragLeave(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('drag-over');
    }
    
    handleFileDrop(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('drag-over');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.processFile(files[0]);
        }
    }
    
    handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            this.processFile(file);
        }
    }
    
    async processFile(file) {
        if (!file.name.toLowerCase().endsWith('.csv')) {
            this.showNotification('error', 'Error', 'Please select a CSV file');
            return;
        }
        
        this.showLoading('Uploading file...');
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await this.apiCall('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            this.lotteryData = response;
            this.showNotification('success', 'Success', `Loaded ${response.entry_count} entries`);
            this.updateUI();
            
        } catch (error) {
            this.showNotification('error', 'Upload Error', error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    // Manual Entry Handling
    async submitManualEntries() {
        const winnersCount = parseInt(this.winnersCountInput.value);
        const entriesText = this.entriesTextarea.value.trim();
        
        if (!winnersCount || winnersCount <= 0) {
            this.showNotification('error', 'Error', 'Please enter a valid number of winners');
            return;
        }
        
        if (!entriesText) {
            this.showNotification('error', 'Error', 'Please enter participant entries');
            return;
        }
        
        this.showLoading('Processing entries...');
        
        try {
            const response = await this.apiCall('/api/manual-entries', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    entries: entriesText,
                    winners_to_pick: winnersCount
                })
            });
            
            this.lotteryData = response;
            this.showNotification('success', 'Success', `Loaded ${response.entry_count} entries`);
            this.updateUI();
            
        } catch (error) {
            this.showNotification('error', 'Entry Error', error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    // Lottery Management
    async shuffleLottery() {
        const randomizationMode = document.querySelector('input[name="randomization"]:checked').value;
        
        this.showLoading('Shuffling lottery...');
        
        try {
            const response = await this.apiCall('/api/shuffle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode: randomizationMode })
            });
            
            this.lotteryData = { ...this.lotteryData, ...response };
            this.showNotification('success', 'Ready to Draw', 'Lottery has been shuffled!');
            this.updateUI();
            
        } catch (error) {
            this.showNotification('error', 'Shuffle Error', error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    async drawNextWinner() {
        this.showLoading('Drawing winner...');
        
        try {
            const response = await this.apiCall('/api/draw-winner', {
                method: 'POST'
            });
            
            const winner = response.winner;
            this.winners.push(winner);
            this.lotteryData.is_completed = response.is_completed;
            
            this.showWinner(winner);
            this.addWinnerToList(winner);
            
            if (response.is_completed) {
                this.showNotification('success', 'Draw Complete', 'All winners have been drawn!');
                this.updateUI();
            } else {
                this.updateDrawProgress(response.remaining_count, response.total_drawn);
            }
            
        } catch (error) {
            this.showNotification('error', 'Draw Error', error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    async resetLottery() {
        if (confirm('Are you sure you want to reset the lottery? This will clear all data.')) {
            this.showLoading('Resetting lottery...');
            
            try {
                await this.apiCall('/api/reset', { method: 'POST' });
                
                this.lotteryData = null;
                this.winners = [];
                this.currentState = 'input';
                
                // Clear form inputs
                this.winnersCountInput.value = '';
                this.entriesTextarea.value = '';
                this.fileInput.value = '';
                
                this.updateUI();
                this.showNotification('success', 'Reset Complete', 'Lottery has been reset');
                
            } catch (error) {
                this.showNotification('error', 'Reset Error', error.message);
            } finally {
                this.hideLoading();
            }
        }
    }
    
    async exportResults() {
        try {
            this.showLoading('Preparing export...');
            
            const response = await fetch('/api/export');
            
            if (!response.ok) {
                throw new Error('Export failed');
            }
            
            // Get filename from response headers
            const contentDisposition = response.headers.get('content-disposition');
            const filename = contentDisposition ? 
                contentDisposition.split('filename=')[1].replace(/[\"]/g, '') : 
                'lottery_results.csv';
            
            // Create download
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            this.showNotification('success', 'Export Complete', 'Results downloaded successfully');
            
        } catch (error) {
            this.showNotification('error', 'Export Error', 'Failed to export results');
        } finally {
            this.hideLoading();
        }
    }
    
    // UI Updates
    updateUI() {
        if (!this.lotteryData) {
            this.showSection('input');
            return;
        }
        
        if (this.lotteryData.is_completed) {
            this.showSection('results');
            this.updateResultsDisplay();
        } else if (this.lotteryData.is_shuffled) {
            this.showSection('drawing');
            this.updateDrawingDisplay();
        } else {
            this.showSection('config');
            this.updateConfigDisplay();
        }
    }
    
    showSection(sectionName) {
        const sections = [this.inputSection, this.configSection, this.drawingSection, this.resultsSection];
        sections.forEach(section => section.classList.add('hidden'));
        
        switch (sectionName) {
            case 'input':
                this.inputSection.classList.remove('hidden');
                break;
            case 'config':
                this.configSection.classList.remove('hidden');
                break;
            case 'drawing':
                this.drawingSection.classList.remove('hidden');
                break;
            case 'results':
                this.resultsSection.classList.remove('hidden');
                break;
        }
        
        this.currentState = sectionName;
    }
    
    updateConfigDisplay() {
        const stats = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>${this.lotteryData.entry_count}</strong> entries loaded<br>
                    <small>Drawing <strong>${this.lotteryData.winners_to_pick}</strong> winners</small>
                </div>
                <div style="text-align: right;">
                    <small>Source: ${this.lotteryData.source}</small>
                </div>
            </div>
        `;
        this.configStats.innerHTML = stats;
    }
    
    updateDrawingDisplay() {
        const drawn = this.winners.length;
        const total = this.lotteryData.winners_to_pick;
        
        this.drawProgress.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>Progress: <strong>${drawn}/${total}</strong> winners drawn</div>
                <div>${total - drawn} remaining</div>
            </div>
        `;
        
        this.drawWinnerBtn.textContent = drawn === 0 ? 'Draw First Winner' : 'Draw Next Winner';
        this.drawWinnerBtn.disabled = false;
    }
    
    updateResultsDisplay() {
        const stats = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>${this.winners.length}</strong> winners drawn<br>
                    <small>from ${this.lotteryData.entry_count} total entries</small>
                </div>
                <div style="text-align: right;">
                    <small>Draw completed</small>
                </div>
            </div>
        `;
        this.resultsStats.innerHTML = stats;
        
        // Populate winners list
        this.winnersList.innerHTML = '';
        this.winners.forEach(winner => {
            this.addWinnerToList(winner);
        });
    }
    
    updateDrawProgress(remaining, totalDrawn) {
        const total = this.lotteryData.winners_to_pick;
        
        this.drawProgress.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>Progress: <strong>${totalDrawn}/${total}</strong> winners drawn</div>
                <div>${remaining} remaining</div>
            </div>
        `;
    }
    
    showWinner(winner) {
        this.currentWinner.classList.remove('hidden');
        this.currentWinner.innerHTML = `
            <div class="winner-rank">#${winner.rank}</div>
            <div class="winner-id">${winner.registration_no}</div>
            <div class="winner-timestamp">Drawn at ${new Date(winner.picked_at).toLocaleTimeString()}</div>
        `;
        
        // Auto-hide after 3 seconds
        setTimeout(() => {
            this.currentWinner.classList.add('hidden');
        }, 3000);
    }
    
    addWinnerToList(winner) {
        const winnerElement = document.createElement('div');
        winnerElement.className = 'winner-item';
        winnerElement.innerHTML = `
            <div class="winner-rank-badge">#${winner.rank}</div>
            <div class="winner-info">
                <div class="winner-name">${winner.registration_no}</div>
                <div class="winner-time">Drawn at ${new Date(winner.picked_at).toLocaleTimeString()}</div>
            </div>
        `;
        this.winnersList.appendChild(winnerElement);
    }
    
    // Utility Methods
    async apiCall(url, options = {}) {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
    
    showLoading(message = 'Loading...') {
        this.loadingOverlay.querySelector('.loading-text').textContent = message;
        this.loadingOverlay.classList.remove('hidden');
    }
    
    hideLoading() {
        this.loadingOverlay.classList.add('hidden');
    }
    
    showNotification(type, title, message) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <div class="notification-title">${title}</div>
            <div class="notification-message">${message}</div>
        `;
        
        this.notificationContainer.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            notification.remove();
        }, 5000);
        
        // Click to dismiss
        notification.addEventListener('click', () => {
            notification.remove();
        });
    }
}

// Initialize the app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.lotteryApp = new LotteryApp();
});