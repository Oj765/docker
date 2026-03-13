import { useState, useEffect } from 'react';

/**
 * Hook to poll for graph alerts (coordinated bursts).
 */
const useGraphAlerts = () => {
    const [alerts, setAlerts] = useState([]);

    useEffect(() => {
        const checkAlerts = async () => {
            try {
                // In a real app, this would be a specific alert endpoint
                const response = await fetch('http://localhost:8000/graph?timeRange=24h');
                const result = await response.json();
                
                if (result.success && result.data.links) {
                    const burstLinks = result.data.links.filter(l => l.burst_detected);
                    if (burstLinks.length > 0) {
                        setAlerts(prev => [...burstLinks, ...prev].slice(0, 10));
                        
                        // If there's a new burst, trigger notification logic
                        // (Would normally call a notification service here)
                    }
                }
            } catch (error) {
                console.error("Alert polling error:", error);
            }
        };

        const interval = setInterval(checkAlerts, 60000); // Poll every minute
        checkAlerts(); // Initial check

        return () => clearInterval(interval);
    }, []);

    return { alerts };
};

export default useGraphAlerts;