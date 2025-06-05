import pandas as pd
import matplotlib.pyplot as plt
import os

def analyze_response_times(csv_file='response_times.csv'):
    """
    Analyzes response times from a CSV file and generates a visualization.
    
    Args:
        csv_file (str): Path to the CSV file containing response times
    """
    # Check if file exists
    if not os.path.exists(csv_file):
        print(f"Error: File {csv_file} not found.")
        return
    
    # Read the CSV file
    try:
        df = pd.read_csv(csv_file)
        print("Data loaded successfully:")
        print(df.head())
        
        # Check if there are any errors in the data
        if df['ResponseTimeSeconds'].dtype == object:
            print("Warning: Non-numeric values found in response times.")
            # Filter out non-numeric values
            df = df[pd.to_numeric(df['ResponseTimeSeconds'], errors='coerce').notna()]
            df['ResponseTimeSeconds'] = pd.to_numeric(df['ResponseTimeSeconds'])
        
        # Calculate average response time
        avg_response_time = df['ResponseTimeSeconds'].mean()
        print(f"Average response time: {avg_response_time:.4f} seconds")
        
        # Create a line chart
        plt.figure(figsize=(10, 6))
        plt.plot(df['QueryNumber'], df['ResponseTimeSeconds'], marker='o', linestyle='-', color='#66ccff', linewidth=2)
        
        # Add average line
        plt.axhline(y=avg_response_time, color='#ff6666', linestyle='--', label=f'Average: {avg_response_time:.4f}s')
        
        # Add labels and title
        plt.xlabel('Query Number', fontsize=12)
        plt.ylabel('Response Time (seconds)', fontsize=12)
        plt.title('AI Museum Chatbot Response Time Analysis', fontsize=14)
        
        # Customize grid and appearance
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.xticks(df['QueryNumber'])
        
        # Add legend
        plt.legend()
        
        # Add text annotations for each point
        for i, row in df.iterrows():
            plt.annotate(f"{row['ResponseTimeSeconds']:.3f}s", 
                         (row['QueryNumber'], row['ResponseTimeSeconds']),
                         textcoords="offset points", 
                         xytext=(0, 10), 
                         ha='center')
        
        # Adjust layout
        plt.tight_layout()
        
        # Save the chart
        plt.savefig('response_time_chart.png', dpi=300, bbox_inches='tight')
        print("Chart saved as response_time_chart.png")
        
        # Show the chart
        plt.show()
        
    except Exception as e:
        print(f"Error analyzing data: {e}")

if __name__ == "__main__":
    analyze_response_times()