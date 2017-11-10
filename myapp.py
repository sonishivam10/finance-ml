from flask import Flask, render_template, redirect, url_for, request
from sklearn import preprocessing, cross_validation, svm
from sklearn.linear_model import LinearRegression
from sklearn.svm import SVR
from os import listdir
from os.path import isfile, join
import os, os.path
import numpy as np
import pandas as pd
import time, datetime
import subprocess
import pickle
import math

app = Flask(__name__)

onlyfiles = [f for f in listdir(os.path.dirname(os.path.realpath(__file__))+'/data_files/') if isfile(join(os.path.dirname(os.path.realpath(__file__))+'/data_files/', f))]

dname = os.path.dirname(os.path.abspath(__file__))
onlyfiles.sort()

@app.route('/')
def main():
	return render_template('home.html')

@app.route('/stockselect')
def stockselect():
	return render_template('stockselect.html', files=onlyfiles)
	
@app.route('/updateprices')
def updateprices():
	subprocess.call(['gnome-terminal', '-e', 'python3 '+dname+'/data_extractor.py'])
	return render_template('home.html')
	
@app.route('/result',methods = ['POST','GET'])
def result():
	if request.method == 'POST':
		selected_stock = request.form['file_select']
		
		os.chdir(dname)
		
		df = pd.read_csv(os.path.join('data_files',selected_stock))

		#preprocessing the data
		df = df[['Adj. Open',  'Adj. High',  'Adj. Low',  'Adj. Close', 'Adj. Volume']]
		#measure of volatility
		df['HL_PCT'] = (df['Adj. High'] - df['Adj. Low']) / df['Adj. Low'] * 100.0
		df['PCT_change'] = (df['Adj. Close'] - df['Adj. Open']) / df['Adj. Open'] * 100.0
		df = df[['Adj. Close', 'HL_PCT', 'PCT_change', 'Adj. Volume']]
		forecast_col = 'Adj. Close'
		df.fillna(value=-99999, inplace=True)
		forecast_out = int(math.ceil(0.01 * len(df)))
		df['label'] = df[forecast_col].shift(-forecast_out)

		X = np.array(df.drop(['label'],1))
		X = preprocessing.scale(X)
		X_lately = X[-forecast_out:]
		X = X[:-forecast_out]

		df.dropna(inplace=True)

		y = np.array(df['label'])

		X_train, X_test, y_train, y_test = cross_validation.train_test_split(X, y, test_size=0.2)
		
		loaded_model = pickle.load(open(join(dname+'/models/', selected_stock+'.sav'),'rb'))
		
		confidence = loaded_model.score(X_test, y_test)
		temp = str(confidence)
		
		'''
		forecast_set = loaded_model.predict(X_lately)
		df['Forecast'] = np.nan
		last_date = df.iloc[-1].name
		print(last_date)
		last_unix = last_date.timestamp()
		one_day = 86400
		next_unix = last_unix + one_day

		for i in forecast_set:
			next_date = datetime.datetime.fromtimestamp(next_unix)
			next_unix += 86400
			df.loc[next_date] = [np.nan for _ in range(len(df.columns)-1)]+[i]

		print( df.tail())
		
		'''
		
		return render_template("result.html",result = temp)

@app.route('/train',methods = ['POST','GET'])
def train():
	if request.method == 'POST':
		selected_stock = request.form['file_select']
		os.chdir(dname)
		
		df = pd.read_csv(os.path.join('data_files',selected_stock))

		#preprocessing the data
		df = df[['Adj. Open',  'Adj. High',  'Adj. Low',  'Adj. Close', 'Adj. Volume']]
		#measure of volatility
		df['HL_PCT'] = (df['Adj. High'] - df['Adj. Low']) / df['Adj. Low'] * 100.0
		df['PCT_change'] = (df['Adj. Close'] - df['Adj. Open']) / df['Adj. Open'] * 100.0
		df = df[['Adj. Close', 'HL_PCT', 'PCT_change', 'Adj. Volume']]
		forecast_col = 'Adj. Close'
		df.fillna(value=-99999, inplace=True)
		forecast_out = int(math.ceil(0.01 * len(df)))
		df['label'] = df[forecast_col].shift(-forecast_out)

		X = np.array(df.drop(['label'],1))
		X = preprocessing.scale(X)
		X_lately = X[-forecast_out:]
		X = X[:-forecast_out]

		df.dropna(inplace=True)

		y = np.array(df['label'])

		X_train, X_test, y_train, y_test = cross_validation.train_test_split(X, y, test_size=0.2)
		clf = SVR()
		clf.fit(X_train, y_train)
		
		pickle.dump(clf,open(join(dname+'/models/', selected_stock+'.sav'),'wb'))
		
		return stockselect()

@app.route('/trainall',methods = ['POST','GET'])
def trainall():
	if request.method == 'POST':
		subprocess.call(['gnome-terminal', '-e', 'python3 '+dname+'/trainall.py'])
		
		return stockselect()


@app.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)

def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(app.root_path,
                                     endpoint, filename)
            values['q'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)

if __name__ == '__main__':
	app.run(debug = True)