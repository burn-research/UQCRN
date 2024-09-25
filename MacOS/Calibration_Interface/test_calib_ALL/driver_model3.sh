echo "Executing driver.sh"

# The first input is params.in.n, get his name into the variable f1
f1=$1
echo "f1 is $f1"

# Extract the last number from the name as a string
str=$1
i=$((${#str}-1))
n=${str:$i:1}

# Create new directory workdir.n
fname="Workdir."
fname+=$n
mkdir $fname

# Copy the input files to the new directory, as well as the python interface
# cp -a CRN_Model_2/* $fname

# Copy params.in.1
cp $1 $fname
echo "$1 copied to $fname"

# Copy the interface
cp interface_model3.py $fname
cp smart_sensors.csv $fname

# Enter the new directory
echo "All files from CRN_Model copied to $fname"

# Launch the python interface
cd $fname
python3 interface_model3.py $1 $2

# Move in the previous folder the output files
mv $2 ../

# Return to working folder
cd ../







