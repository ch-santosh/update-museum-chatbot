import subprocess
import csv
import time
import os

def measure_response_times(url, num_requests=10):
    """
    Sends HTTP requests to the specified URL using curl and records response times.
    
    Args:
        url (str): The URL to send requests to
        num_requests (int): Number of requests to send
    
    Returns:
        list: List of response times in seconds
    """
    print(f"Measuring response times for {url}...")
    response_times = []
    
    # Create CSV file
    with open('response_times.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['QueryNumber', 'ResponseTimeSeconds'])
        
        for i in range(1, num_requests + 1):
            print(f"Sending request {i}/{num_requests}...")
            
            # Replace the curl_command in measure_response_times.py with this:
            curl_command = [
                'curl', 
                '-s', 
                '-o', 'NUL',  # Use NUL instead of /dev/null on Windows
                '-w', '%{time_total}',
                url
            ]
            
            try:
                # Execute curl command and capture output
                result = subprocess.run(curl_command, capture_output=True, text=True, check=True)
                response_time = float(result.stdout.strip())
                
                # Add to our list and write to CSV
                response_times.append(response_time)
                writer.writerow([i, response_time])
                
                print(f"Request {i}: {response_time:.4f} seconds")
                
                # Small delay between requests to avoid overwhelming the server
                time.sleep(1)
                
            except subprocess.CalledProcessError as e:
                print(f"Error on request {i}: {e}")
                # Write error to CSV
                writer.writerow([i, "Error"])
    
    print(f"Measurement complete. Results saved to response_times.csv")
    return response_times

if __name__ == "__main__":
    # URL of the Streamlit app
    streamlit_url = "http://localhost:8501"
    
    # Check if the script is in the correct directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Running from directory: {script_dir}")
    
    # Measure response times
    times = measure_response_times(streamlit_url)
    
    # Calculate and display average
    if times:
        avg_time = sum(times) / len(times)
        print(f"Average response time: {avg_time:.4f} seconds")