/**
 * MediScript Pro - Complete Prescription Canvas Functionality
 * Advanced digital drawing tools for medical prescriptions
 */

class PrescriptionCanvas {
    constructor() {
        this.canvas = document.getElementById('prescription-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.signatureCanvas = document.getElementById('signature-canvas');
        this.signatureCtx = this.signatureCanvas.getContext('2d');
        
        this.isDrawing = false;
        this.currentTool = 'pen';
        this.currentColor = '#000000';
        this.currentSize = 2;
        this.pages = [];
        this.currentPageIndex = 0;
        this.history = [];
        this.historyStep = -1;
        this.savedSignature = null;
        
        this.initializeCanvas();
        this.setupEventListeners();
        this.loadSavedSignature();
    }
    
    initializeCanvas() {
        // Set current date and time
        const now = new Date();
        const dateInput = document.getElementById('prescription-date');
        const timeInput = document.getElementById('prescription-time');
        
        if (dateInput) {
            dateInput.value = now.toISOString().split('T')[0];
        }
        if (timeInput) {
            timeInput.value = now.toTimeString().split(':').slice(0, 2).join(':');
        }
        
        // Initialize first page
        this.pages.push('');
        this.saveState();
        this.updatePageInfo();
        
        // Set canvas properties
        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';
        this.signatureCtx.lineCap = 'round';
        this.signatureCtx.lineJoin = 'round';
        
        // Set white background
        this.ctx.fillStyle = 'white';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        this.signatureCtx.fillStyle = 'white';
        this.signatureCtx.fillRect(0, 0, this.signatureCanvas.width, this.signatureCanvas.height);
    }
    
    setupEventListeners() {
        // Main canvas events
        this.setupCanvasEvents(this.canvas, this.ctx, false);
        
        // Signature canvas events
        this.setupCanvasEvents(this.signatureCanvas, this.signatureCtx, true);
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));
        
        // Tool panel events
        this.setupToolPanelEvents();
        
        // Window resize
        window.addEventListener('resize', () => this.handleResize());
    }
    
    setupCanvasEvents(canvas, context, isSignature) {
        // Mouse events
        canvas.addEventListener('mousedown', (e) => this.startDrawing(e, context, isSignature));
        canvas.addEventListener('mousemove', (e) => this.draw(e, context, isSignature));
        canvas.addEventListener('mouseup', () => this.stopDrawing(isSignature));
        canvas.addEventListener('mouseout', () => this.stopDrawing(isSignature));
        
        // Touch events for tablets and mobile
        canvas.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            const mouseEvent = new MouseEvent('mousedown', {
                clientX: touch.clientX,
                clientY: touch.clientY
            });
            canvas.dispatchEvent(mouseEvent);
        });
        
        canvas.addEventListener('touchmove', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            const mouseEvent = new MouseEvent('mousemove', {
                clientX: touch.clientX,
                clientY: touch.clientY
            });
            canvas.dispatchEvent(mouseEvent);
        });
        
        canvas.addEventListener('touchend', (e) => {
            e.preventDefault();
            const mouseEvent = new MouseEvent('mouseup', {});
            canvas.dispatchEvent(mouseEvent);
        });
        
        // Prevent scrolling when drawing on touch devices
        canvas.addEventListener('touchstart', (e) => e.preventDefault());
        canvas.addEventListener('touchmove', (e) => e.preventDefault());
    }
    
    setupToolPanelEvents() {
        // Color picker
        const colorPicker = document.getElementById('color-picker');
        if (colorPicker) {
            colorPicker.addEventListener('change', (e) => {
                this.setColor(e.target.value);
            });
        }
        
        // Size slider
        const sizeSlider = document.getElementById('size-slider');
        if (sizeSlider) {
            sizeSlider.addEventListener('input', (e) => {
                this.setSize(e.target.value);
            });
        }
    }
    
    handleKeyboardShortcuts(e) {
        // Ctrl/Cmd + Z for undo
        if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
            e.preventDefault();
            this.undoLast();
        }
        
        // Ctrl/Cmd + Shift + Z for redo
        if ((e.ctrlKey || e.metaKey) && e.key === 'z' && e.shiftKey) {
            e.preventDefault();
            this.redoLast();
        }
        
        // Ctrl/Cmd + Y for redo (alternative)
        if ((e.ctrlKey || e.metaKey) && e.key === 'y') {
            e.preventDefault();
            this.redoLast();
        }
        
        // Ctrl/Cmd + S for save
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            this.savePrescription();
        }
        
        // Page navigation with arrow keys
        if (e.key === 'ArrowLeft' && e.altKey) {
            e.preventDefault();
            this.previousPage();
        }
        
        if (e.key === 'ArrowRight' && e.altKey) {
            e.preventDefault();
            this.nextPage();
        }
        
        // Tool shortcuts
        if (e.key === '1' && e.altKey) {
            e.preventDefault();
            this.setTool('pen');
        }
        
        if (e.key === '2' && e.altKey) {
            e.preventDefault();
            this.setTool('brush');
        }
        
        if (e.key === '3' && e.altKey) {
            e.preventDefault();
            this.setTool('highlighter');
        }
        
        if (e.key === '4' && e.altKey) {
            e.preventDefault();
            this.setTool('eraser');
        }
    }
    
    handleResize() {
        // Responsive canvas handling
        const container = document.querySelector('.canvas-container');
        if (!container) return;
        
        const maxWidth = container.clientWidth - 40;
        
        if (maxWidth < 760 && window.innerWidth < 768) {
            this.canvas.style.width = maxWidth + 'px';
            this.canvas.style.height = (maxWidth * 0.75) + 'px'; // Maintain aspect ratio
        } else {
            this.canvas.style.width = '100%';
            this.canvas.style.height = '500px';
        }
    }
    
    getCanvasCoordinates(e, canvas) {
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        
        return {
            x: (e.clientX - rect.left) * scaleX,
            y: (e.clientY - rect.top) * scaleY
        };
    }
    
    startDrawing(e, context, isSignature) {
        this.isDrawing = true;
        const coords = this.getCanvasCoordinates(e, isSignature ? this.signatureCanvas : this.canvas);
        
        context.beginPath();
        context.moveTo(coords.x, coords.y);
        
        // Set drawing properties based on tool
        this.setDrawingProperties(context);
        
        // Add vibration feedback on mobile
        if ('vibrate' in navigator) {
            navigator.vibrate(10);
        }
    }
    
    draw(e, context, isSignature) {
        if (!this.isDrawing) return;
        
        const coords = this.getCanvasCoordinates(e, isSignature ? this.signatureCanvas : this.canvas);
        context.lineTo(coords.x, coords.y);
        context.stroke();
    }
    
    stopDrawing(isSignature) {
        if (this.isDrawing) {
            this.isDrawing = false;
            if (!isSignature) {
                this.saveState();
            }
        }
    }
    
    setDrawingProperties(context) {
        switch (this.currentTool) {
            case 'pen':
                context.globalCompositeOperation = 'source-over';
                context.globalAlpha = 1.0;
                context.strokeStyle = this.currentColor;
                context.lineWidth = this.currentSize;
                break;
                
            case 'brush':
                context.globalCompositeOperation = 'source-over';
                context.globalAlpha = 0.8;
                context.strokeStyle = this.currentColor;
                context.lineWidth = this.currentSize * 1.5;
                break;
                
            case 'highlighter':
                context.globalCompositeOperation = 'source-over';
                context.globalAlpha = 0.3;
                context.strokeStyle = this.currentColor;
                context.lineWidth = this.currentSize * 3;
                break;
                
            case 'eraser':
                context.globalCompositeOperation = 'destination-out';
                context.globalAlpha = 1.0;
                context.lineWidth = this.currentSize * 2;
                break;
        }
        
        context.lineCap = 'round';
        context.lineJoin = 'round';
    }
    
    setTool(tool) {
        this.currentTool = tool;
        
        // Update UI
        document.querySelectorAll('.tool-btn').forEach(btn => btn.classList.remove('active'));
        const toolBtn = document.getElementById(tool + '-tool');
        if (toolBtn) {
            toolBtn.classList.add('active');
        }
        
        // Update cursor
        const cursor = tool === 'eraser' ? 'grab' : 'crosshair';
        this.canvas.style.cursor = cursor;
        this.signatureCanvas.style.cursor = cursor;
        
        // Update canvas properties for immediate visual feedback
        this.setDrawingProperties(this.ctx);
        
        this.showNotification(`${tool.charAt(0).toUpperCase() + tool.slice(1)} tool selected`, 'info');
    }
    
    setColor(color) {
        this.currentColor = color;
        const colorPicker = document.getElementById('color-picker');
        if (colorPicker) {
            colorPicker.value = color;
        }
        
        // Visual feedback - update tool button borders
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.style.borderLeft = this.currentTool !== 'eraser' ? `4px solid ${color}` : 'none';
        });
    }
    
    setSize(size) {
        this.currentSize = parseInt(size);
        const sizeDisplay = document.getElementById('size-display');
        if (sizeDisplay) {
            sizeDisplay.textContent = `Size: ${size}px`;
        }
        
        // Visual feedback - show size preview
        this.showSizePreview(size);
    }
    
    showSizePreview(size) {
        // Create temporary preview circle
        let preview = document.getElementById('size-preview');
        if (!preview) {
            preview = document.createElement('div');
            preview.id = 'size-preview';
            document.body.appendChild(preview);
        }
        
        preview.style.cssText = `
            position: fixed;
            width: ${size * 2}px;
            height: ${size * 2}px;
            background: ${this.currentColor};
            border-radius: 50%;
            pointer-events: none;
            z-index: 9999;
            opacity: 0.7;
            transform: translate(-50%, -50%);
            transition: all 0.2s ease;
        `;
        
        // Follow mouse cursor
        const followMouse = (e) => {
            preview.style.left = e.clientX + 'px';
            preview.style.top = e.clientY + 'px';
        };
        
        document.addEventListener('mousemove', followMouse);
        
        // Remove preview after 2 seconds
        setTimeout(() => {
            if (document.getElementById('size-preview')) {
                document.getElementById('size-preview').remove();
                document.removeEventListener('mousemove', followMouse);
            }
        }, 2000);
    }
    
    clearCanvas() {
        this.ctx.fillStyle = 'white';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        this.saveState();
        
        // Visual feedback
        this.showNotification('Canvas cleared', 'info');
    }
    
    clearSignature() {
        this.signatureCtx.fillStyle = 'white';
        this.signatureCtx.fillRect(0, 0, this.signatureCanvas.width, this.signatureCanvas.height);
        this.showNotification('Signature cleared', 'info');
    }
    
    saveState() {
        this.historyStep++;
        if (this.historyStep < this.history.length) {
            this.history.length = this.historyStep;
        }
        this.history.push(this.canvas.toDataURL());
        this.pages[this.currentPageIndex] = this.canvas.toDataURL();
        
        // Limit history to prevent memory issues
        if (this.history.length > 50) {
            this.history.shift();
            this.historyStep--;
        }
    }
    
    undoLast() {
        if (this.historyStep > 0) {
            this.historyStep--;
            this.loadCanvasState(this.history[this.historyStep]);
            this.showNotification('Undone', 'info');
        } else {
            this.showNotification('Nothing to undo', 'warning');
        }
    }
    
    redoLast() {
        if (this.historyStep < this.history.length - 1) {
            this.historyStep++;
            this.loadCanvasState(this.history[this.historyStep]);
            this.showNotification('Redone', 'info');
        } else {
            this.showNotification('Nothing to redo', 'warning');
        }
    }
    
    loadCanvasState(dataURL) {
        const img = new Image();
        img.onload = () => {
            this.ctx.fillStyle = 'white';
            this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
            this.ctx.drawImage(img, 0, 0);
            this.pages[this.currentPageIndex] = dataURL;
        };
        img.src = dataURL;
    }
    
    addPage() {
        this.pages.push('');
        this.currentPageIndex = this.pages.length - 1;
        this.ctx.fillStyle = 'white';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        this.updatePageInfo();
        this.saveState();
        this.showNotification(`Page ${this.currentPageIndex + 1} added`, 'success');
    }
    
    deletePage() {
        if (this.pages.length > 1) {
            const pageNum = this.currentPageIndex + 1;
            this.pages.splice(this.currentPageIndex, 1);
            
            if (this.currentPageIndex >= this.pages.length) {
                this.currentPageIndex = this.pages.length - 1;
            }
            
            this.loadPage(this.currentPageIndex);
            this.updatePageInfo();
            this.showNotification(`Page ${pageNum} deleted`, 'info');
        } else {
            this.showNotification('Cannot delete the last page', 'warning');
        }
    }
    
    previousPage() {
        if (this.currentPageIndex > 0) {
            this.pages[this.currentPageIndex] = this.canvas.toDataURL();
            this.currentPageIndex--;
            this.loadPage(this.currentPageIndex);
            this.updatePageInfo();
        } else {
            this.showNotification('Already on first page', 'warning');
        }
    }
    
    nextPage() {
        if (this.currentPageIndex < this.pages.length - 1) {
            this.pages[this.currentPageIndex] = this.canvas.toDataURL();
            this.currentPageIndex++;
            this.loadPage(this.currentPageIndex);
            this.updatePageInfo();
        } else {
            this.showNotification('Already on last page', 'warning');
        }
    }
    
    loadPage(pageIndex) {
        if (this.pages[pageIndex] && this.pages[pageIndex] !== '') {
            this.loadCanvasState(this.pages[pageIndex]);
        } else {
            this.ctx.fillStyle = 'white';
            this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
            this.pages[pageIndex] = this.canvas.toDataURL();
        }
    }
    
    updatePageInfo() {
        const pageInfo = document.getElementById('page-info');
        if (pageInfo) {
            pageInfo.textContent = `Page ${this.currentPageIndex + 1} of ${this.pages.length}`;
        }
    }
    
    saveSignature() {
        this.savedSignature = this.signatureCanvas.toDataURL();
        
        // Save to localStorage for persistence
        try {
            localStorage.setItem('mediscript_signature', this.savedSignature);
            this.showNotification('Signature saved', 'success');
        } catch (error) {
            this.showNotification('Error saving signature', 'error');
        }
    }
    
    loadSavedSignature() {
        try {
            const saved = localStorage.getItem('mediscript_signature');
            if (saved) {
                const img = new Image();
                img.onload = () => {
                    this.signatureCtx.fillStyle = 'white';
                    this.signatureCtx.fillRect(0, 0, this.signatureCanvas.width, this.signatureCanvas.height);
                    this.signatureCtx.drawImage(img, 0, 0);
                };
                img.src = saved;
                this.savedSignature = saved;
            }
        } catch (error) {
            console.log('No saved signature found or error loading signature');
        }
    }
    
    savePrescription() {
        try {
            const prescriptionData = {
                pages: this.pages,
                signature: this.signatureCanvas.toDataURL(),
                doctorName: this.getFormValue('doctor-name', 'Dr. Smith'),
                clinicName: this.getFormValue('clinic-name', 'Medical Center'),
                patientName: this.getFormValue('patient-name', 'John Doe'),
                patientAge: this.getFormValue('patient-age', '35'),
                date: this.getFormValue('prescription-date', new Date().toISOString().split('T')[0]),
                time: this.getFormValue('prescription-time', new Date().toTimeString().split(':').slice(0, 2).join(':')),
                timestamp: new Date().toISOString()
            };
            
            const dataStr = JSON.stringify(prescriptionData);
            const blob = new Blob([dataStr], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = `prescription_${prescriptionData.patientName.replace(/\s+/g, '_')}_${prescriptionData.date}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            // Save signature for future use
            localStorage.setItem('mediscript_signature', this.signatureCanvas.toDataURL());
            
            this.showNotification('Prescription saved successfully!', 'success');
        } catch (error) {
            this.showNotification('Error saving prescription', 'error');
        }
    }
    
    getFormValue(elementId, defaultValue) {
        const element = document.getElementById(elementId);
        return element ? element.value || defaultValue : defaultValue;
    }
    
    loadPrescription(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const data = JSON.parse(e.target.result);
                
                // Load pages
                this.pages = data.pages || [];
                this.currentPageIndex = 0;
                
                if (this.pages.length > 0) {
                    this.loadPage(0);
                }
                
                // Load form data
                this.setFormValue('doctor-name', data.doctorName);
                this.setFormValue('clinic-name', data.clinicName);
                this.setFormValue('patient-name', data.patientName);
                this.setFormValue('patient-age', data.patientAge);
                this.setFormValue('prescription-date', data.date);
                this.setFormValue('prescription-time', data.time);
                
                // Load signature
                if (data.signature) {
                    const img = new Image();
                    img.onload = () => {
                        this.signatureCtx.fillStyle = 'white';
                        this.signatureCtx.fillRect(0, 0, this.signatureCanvas.width, this.signatureCanvas.height);
                        this.signatureCtx.drawImage(img, 0, 0);
                    };
                    img.src = data.signature;
                }
                
                this.updatePageInfo();
                this.showNotification('Prescription loaded successfully!', 'success');
            } catch (error) {
                this.showNotification('Error loading prescription file', 'error');
            }
        };
        reader.readAsText(file);
    }
    
    setFormValue(elementId, value) {
        const element = document.getElementById(elementId);
        if (element && value) {
            element.value = value;
        }
    }
    
    printPrescription() {
        const printWindow = window.open('', '_blank');
        const canvasDataURL = this.canvas.toDataURL();
        const signatureDataURL = this.signatureCanvas.toDataURL();
        
        const doctorName = this.getFormValue('doctor-name', 'Dr. Smith');
        const clinicName = this.getFormValue('clinic-name', 'Medical Center');
        const patientName = this.getFormValue('patient-name', 'John Doe');
        const patientAge = this.getFormValue('patient-age', '35');
        const date = this.getFormValue('prescription-date', new Date().toISOString().split('T')[0]);
        const time = this.getFormValue('prescription-time', new Date().toTimeString().split(':').slice(0, 2).join(':'));
        
        printWindow.document.write(`
            <html>
                <head>
                    <title>Prescription - ${patientName}</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 20px; }
                        .header { text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
                        .patient-info { margin-bottom: 20px; }
                        .prescription-canvas { border: 1px solid #ccc; margin: 20px 0; }
                        .signature-section { margin-top: 30px; }
                        @media print { body { margin: 0; } }
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>${clinicName}</h1>
                        <h2>${doctorName}</h2>
                        <p>Date: ${date} | Time: ${time}</p>
                    </div>
                    <div class="patient-info">
                        <h3>Patient Information</h3>
                        <p><strong>Name:</strong> ${patientName}</p>
                        <p><strong>Age:</strong> ${patientAge}</p>
                    </div>
                    <div class="prescription-content">
                        <h3>Prescription</h3>
                        <img src="${canvasDataURL}" class="prescription-canvas" style="max-width: 100%;">
                    </div>
                    <div class="signature-section">
                        <h4>Doctor's Signature</h4>
                        <img src="${signatureDataURL}" style="max-width: 400px; height: 120px; border: 1px solid #ccc;">
                        <p><strong>${doctorName}</strong></p>
                    </div>
                    <script>
                        window.onload = function() {
                            setTimeout(function() {
                                window.print();
                                window.close();
                            }, 500);
                        }
                    </script>
                </body>
            </html>
        `);
        
        printWindow.document.close();
        this.showNotification('Print dialog opened', 'info');
    }
    
    exportPDF() {
        // This is a simplified PDF export - in a real application, 
        // you would use a library like jsPDF
        this.showNotification('PDF export feature would require jsPDF library', 'info');
        
        // Alternative: Save as image
        this.exportAsImage();
    }
    
    exportAsImage() {
        try {
            const link = document.createElement('a');
            link.download = `prescription_${this.getFormValue('patient-name', 'prescription')}_${new Date().toISOString().split('T')[0]}.png`;
            link.href = this.canvas.toDataURL();
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            this.showNotification('Prescription exported as image', 'success');
        } catch (error) {
            this.showNotification('Error exporting image', 'error');
        }
    }
    
    showNotification(message, type = 'info') {
        // Remove existing notification
        const existing = document.querySelector('.notification');
        if (existing) {
            existing.remove();
        }
        
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        // Add to DOM
        document.body.appendChild(notification);
        
        // Show with animation
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        // Hide and remove after 3 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        }, 3000);
    }
    
    // Utility methods for external file operations
    createFileInput() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        input.onchange = (e) => {
            const file = e.target.files[0];
            if (file) {
                this.loadPrescription(file);
            }
        };
        return input;
    }
    
    loadPrescriptionFromFile() {
        const input = this.createFileInput();
        input.click();
    }
    
    // Advanced drawing features
    addText() {
        const text = prompt('Enter text to add:');
        if (text) {
            this.ctx.font = `${this.currentSize * 8}px Arial`;
            this.ctx.fillStyle = this.currentColor;
            this.ctx.fillText(text, 50, 50);
            this.saveState();
            this.showNotification('Text added', 'success');
        }
    }
    
    addStamp() {
        // Add a simple circular stamp
        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height / 2;
        const radius = 30;
        
        this.ctx.beginPath();
        this.ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
        this.ctx.strokeStyle = this.currentColor;
        this.ctx.lineWidth = 3;
        this.ctx.stroke();
        
        this.ctx.font = '12px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.fillStyle = this.currentColor;
        this.ctx.fillText('APPROVED', centerX, centerY);
        
        this.saveState();
        this.showNotification('Stamp added', 'success');
    }
    
    // Zoom functionality
    zoomIn() {
        const currentScale = parseFloat(this.canvas.style.transform.replace(/[^\d.]/g, '') || 1);
        const newScale = Math.min(currentScale * 1.2, 3);
        this.canvas.style.transform = `scale(${newScale})`;
        this.showNotification(`Zoomed to ${Math.round(newScale * 100)}%`, 'info');
    }
    
    zoomOut() {
        const currentScale = parseFloat(this.canvas.style.transform.replace(/[^\d.]/g, '') || 1);
        const newScale = Math.max(currentScale / 1.2, 0.5);
        this.canvas.style.transform = `scale(${newScale})`;
        this.showNotification(`Zoomed to ${Math.round(newScale * 100)}%`, 'info');
    }
    
    resetZoom() {
        this.canvas.style.transform = 'scale(1)';
        this.showNotification('Zoom reset', 'info');
    }
}

// Initialize the prescription canvas when DOM is loaded
let prescriptionCanvas;

document.addEventListener('DOMContentLoaded', function() {
    try {
        prescriptionCanvas = new PrescriptionCanvas();
        console.log('PrescriptionCanvas initialized successfully');
    } catch (error) {
        console.error('Error initializing PrescriptionCanvas:', error);
    }
});

// Export for global access
if (typeof window !== 'undefined') {
    window.PrescriptionCanvas = PrescriptionCanvas;
}