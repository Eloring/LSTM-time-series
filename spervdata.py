from math import sqrt
from numpy import concatenate
import numpy as np
from pandas import read_csv
from pandas import DataFrame
from pandas import concat
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
from keras.layers.core import Dense, Activation, Dropout
from matplotlib import pyplot

# convert series to supervised learning
def series_to_supervised(data, n_in=1, n_out=1, dropnan=True):
	n_vars = 1 if type(data) is list else data.shape[1]
	df = DataFrame(data)
	cols, names = list(), list()
	# input sequence (t-n, ... t-1)
	for i in range(n_in, 0, -1):
		cols.append(df.shift(i))
		names += [('var%d(t-%d)' % (j+1, i)) for j in range(n_vars)]
	# forecast sequence (t, t+1, ... t+n)
	for i in range(0, n_out):
		cols.append(df.shift(-i))
		if i == 0:
			names += [('var%d(t)' % (j+1)) for j in range(n_vars)]
		else:
			names += [('var%d(t+%d)' % (j+1, i)) for j in range(n_vars)]
	# put it all together
	agg = concat(cols, axis=1)
	agg.columns = names
	# drop rows with NaN values
	if dropnan:
		agg.dropna(inplace=True)
	return agg

# load dataset
dataset = read_csv('sensordata.csv', header = 0, index_col=0)
values = dataset.values
# ensure all data is float
values = values.astype('float32')
# normalise features
scaler = MinMaxScaler(feature_range=(0,1))
scaled = scaler.fit_transform(values)
# frame as supervised learning
n_mins = 5
n_features = 24
reframed = series_to_supervised(scaled, n_mins, 1)
# drop columns we don't want to predict
print(reframed.shape)

# split into train and test sets
values = reframed.values
n_train_mins = 4 * 24 * 60
train = values[:n_train_mins, :]
test = values[n_train_mins:, :]
# split into input and outputs
n_obs = n_mins * n_features
train_X, train_y = train[:, :n_obs], train[:, -1]
test_X,  test_y =test[:, :n_obs], test[:,-1]
# reshape input to be 3D [samples, timesteps, features]
train_X = train_X.reshape((train_X.shape[0], n_mins, n_features))
test_X = test_X.reshape((test_X.shape[0], n_mins, n_features))
print(train_X.shape, train_y.shape, test_X.shape, test_y.shape)

# design network
layers = [0,120,0,0,1]
model = Sequential()

model.add(LSTM(
	layers[1],
	input_shape=(train_X.shape[1], train_X.shape[2]),
	return_sequences=False))
model.add(Dropout(0.2))

#model.add(LSTM(
#        layers[2],
#        return_sequences=False))
#model.add(Dropout(0.2))

# model.add(LSTM(
#        layers[3],
#        return_sequences=False))
# model.add(Dropout(0.2))

model.add(Dense(layers[4]))
model.add(Activation("linear"))

model.compile(loss='mae', optimizer='adam')
# fit network
history = model.fit(train_X, train_y, epochs = 50, batch_size=512, validation_data=(test_X, test_y), verbose=2, shuffle=False)
# plot history
pyplot.plot(history.history['loss'], label='train')
pyplot.plot(history.history['val_loss'], label='test')
pyplot.legend()
pyplot.show()

# make a prediction
yhat = model.predict(test_X)
test_X = test_X.reshape((test_X.shape[0], n_mins*n_features))

# invert scaling for forecast
inv_yhat = concatenate((test_X[:, -24:-1],yhat), axis=1)
inv_yhat = scaler.inverse_transform(inv_yhat)
inv_yhat = inv_yhat[:,-1]

# invert scaling for actual
test_y = test_y.reshape((len(test_y), 1))
inv_y = concatenate((test_X[:, -24:-1],test_y), axis=1)
inv_y = scaler.inverse_transform(inv_y)
inv_y = inv_y[:,-1]
# calculate RMSE 平方根均方误差
rmse = sqrt(mean_squared_error(inv_y, inv_yhat))
print('Test RMSE: %.3f' % rmse)
# calculate MAPE 平均绝对百分误差
mape = np.mean(np.fabs((inv_y - inv_yhat) / inv_y)) * 100
print('Test mape: %d' % mape)
 
# plot
pyplot.plot([x for x in range(1,inv_yhat.shape[0]+1)], inv_yhat, linestyle='-', color='red', label='prediction model')
pyplot.plot([x for x in range(1,inv_y.shape[0]+1)], inv_y, linestyle='-', color='blue', label='test model')
pyplot.legend(loc=1, prop={'size': 12})
pyplot.show()
